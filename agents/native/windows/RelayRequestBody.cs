using System.Text;
using System.Text.Json;

internal static class RelayRequestBody
{
    // The short-text relay requires Content-Length; JsonContent streams chunked HTTP.
    internal static HttpContent Create<T>(T value) =>
        new StringContent(JsonSerializer.Serialize(value), Encoding.UTF8, "application/json");
}
