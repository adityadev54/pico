using System.Net;
using System.Text.Json;

internal sealed record PairingResult(string? Token, string? Error);

internal static class PairingConnection
{
    internal static async Task<PairingResult> ClaimAsync(HttpClient client, string relay, string code, string computerName)
    {
        try {
            using var content = RelayRequestBody.Create(new { code, os = "windows", name = computerName });
            using var response = await client.PostAsync(relay.TrimEnd('/') + "/claim", content);
            string body = await response.Content.ReadAsStringAsync();
            using var json = TryParse(body);
            if (response.StatusCode == HttpStatusCode.OK) {
                if (json?.RootElement.TryGetProperty("token", out var token) == true && token.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(token.GetString()))
                    return new(token.GetString(), null);
                return new(null, "Pico returned an incomplete connection. Try again shortly.");
            }
            if (json?.RootElement.TryGetProperty("error", out var error) == true && error.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(error.GetString()))
                return new(null, error.GetString());
            return new(null, response.StatusCode switch {
                HttpStatusCode.BadRequest => "This code is incorrect or expired. Get a new code on your phone.",
                HttpStatusCode.Conflict => "Unpair the connected computer on your phone, then get a new code.",
                HttpStatusCode.TooManyRequests => "Too many attempts. Please wait 10 minutes before trying again.",
                _ => "Pico is temporarily unavailable. Try again shortly."
            });
        }
        catch (OperationCanceledException) { return new(null, "Pico took too long to respond. Check your connection and try again."); }
        catch (HttpRequestException) { return new(null, "Couldn’t reach Pico. Check your internet connection, firewall or proxy."); }
    }

    static JsonDocument? TryParse(string value)
    {
        try { var json = JsonDocument.Parse(value); if (json.RootElement.ValueKind == JsonValueKind.Object) return json; json.Dispose(); }
        catch (JsonException) { }
        return null;
    }
}
