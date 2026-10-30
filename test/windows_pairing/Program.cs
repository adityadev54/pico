using System.Net;
using System.Text;
using System.Text.Json;
var cases = new (HttpStatusCode status, string body, string? expected)[] {
 (HttpStatusCode.OK, "{\"token\":\"test-device-token\"}", null),
 (HttpStatusCode.BadRequest, "{\"error\":\"This code is incorrect, expired, or already used.\"}", "expired"),
 (HttpStatusCode.Conflict, "{\"error\":\"Unpair the existing computer first.\"}", "Unpair"),
 (HttpStatusCode.TooManyRequests, "{}", "10 minutes"),
 (HttpStatusCode.ServiceUnavailable, "<html>Unavailable</html>", "temporarily unavailable"),
 (HttpStatusCode.OK, "not-json", "incomplete"),
 (HttpStatusCode.OK, "[]", "incomplete")
};
foreach (var c in cases) {
 using var client = new HttpClient(new Fake(c.status,c.body));
 var result = await PairingConnection.ClaimAsync(client,"https://example.test","123456","Test PC");
 if (c.expected == null ? result.Token != "test-device-token" || result.Error != null : result.Error?.Contains(c.expected) != true) throw new Exception("Wrong error mapping");
}
foreach (bool timeout in new[]{false,true}) {
 using var client = new HttpClient(new Fake(HttpStatusCode.OK,"",timeout ? new TaskCanceledException() : new HttpRequestException()));
 var result=await PairingConnection.ClaimAsync(client,"https://example.test","123456","Test PC");
 if (result.Error?.Contains(timeout ? "too long" : "Couldn’t reach") != true) throw new Exception("Network errors missing");
}
using (var poll = RelayRequestBody.Create(new System.Text.Json.Nodes.JsonObject())) {
 if (poll.Headers.ContentLength != 2 || await poll.ReadAsStringAsync() != "{}") throw new Exception("Polling body must also have a fixed length");
}
var placements = new[] {
 (new System.Drawing.Rectangle(1720, 850, 180, 180), new System.Drawing.Size(312, 382), new System.Drawing.Rectangle(0, 0, 1920, 1040)),
 (new System.Drawing.Rectangle(10, 20, 180, 180), new System.Drawing.Size(312, 382), new System.Drawing.Rectangle(0, 0, 1920, 1040)),
 (new System.Drawing.Rectangle(1720, 5, 180, 180), new System.Drawing.Size(624, 764), new System.Drawing.Rectangle(0, 0, 1920, 1040)),
 (new System.Drawing.Rectangle(-1900, 800, 180, 180), new System.Drawing.Size(312, 382), new System.Drawing.Rectangle(-1920, 0, 1920, 1040)),
 (new System.Drawing.Rectangle(600, 500, 180, 180), new System.Drawing.Size(312, 382), new System.Drawing.Rectangle(0, 0, 1920, 1040))
};
foreach (var (agent,size,work) in placements) {
 var bounds=CompanionMenuPlacement.NextTo(agent,size,work,12);
 if (!work.Contains(bounds) || bounds.IntersectsWith(agent)) throw new Exception("Menu must stay on-screen beside the companion");
}
Console.WriteLine("15 Windows pairing, request-framing and menu-placement checks passed.");
sealed class Fake(HttpStatusCode status,string body,Exception? error=null) : HttpMessageHandler {
 protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken cancel) {
  if (request.Content!.Headers.ContentLength is not > 0) throw new Exception("Relay requests must include Content-Length");
  var sent=JsonDocument.Parse(await request.Content.ReadAsStringAsync());
  if(sent.RootElement.GetProperty("os").GetString()!="windows" || sent.RootElement.GetProperty("code").GetString()!="123456") throw new Exception("Invalid pairing payload");
  if(error != null) throw error;
  return new HttpResponseMessage(status){Content=new StringContent(body,Encoding.UTF8,"application/json")};
 }
}
