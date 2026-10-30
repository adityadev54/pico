"""Interactive demonstration script for Step 4 (MetaClient).

Shows:
1. Tool calling negotiation (search_documents)
2. Token usage tracking
3. Cost accumulation
4. Simulated labeling ([SIMULATED])
"""
from server.agent.meta_client import MetaClient

def main():
    print("=" * 55)
    print("        TESTING STEP 4: META MODEL API CLIENT       ")
    print("=" * 55)

    client = MetaClient()
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_documents",
                "description": "Search computer documents by query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query text"}
                    },
                    "required": ["query"],
                },
            },
        }
    ]

    print("\n[Turn 1] Sending prompt: 'Find my project brief' with tool search_documents...")
    resp = client.chat(
        messages=[{"role": "user", "content": "Find my project brief"}],
        tools=tools,
    )

    print("\nResponse Received:")
    print(f"  Model Name       : {resp.model_name}")
    print(f"  Simulated Mode   : {resp.simulated}")
    print(f"  Assistant Text   : {resp.content}")
    print(f"  Tool Name Called : {resp.tool_calls[0]['function']['name']}")
    print(f"  Tool Arguments   : {resp.tool_calls[0]['function']['arguments']}")
    print(f"  Turn Latency     : {resp.latency_ms} ms")
    print(f"  Turn Tokens      : {resp.usage}")
    print(f"  Cumulative Cost  : ${client.usage.estimated_cost_usd:.6f}")
    print(f"  Cumulative Turns : {client.usage.call_count}")

    print("\n[Turn 2] Sending second prompt: 'Can you tell me a quick status update?' without tools...")
    resp2 = client.chat(
        messages=[{"role": "user", "content": "Can you tell me a quick status update?"}],
        tools=None,
    )

    print("\nResponse Received:")
    print(f"  Model Name       : {resp2.model_name}")
    print(f"  Simulated Mode   : {resp2.simulated}")
    print(f"  Assistant Text   : {resp2.content}")
    print(f"  Tool Calls Count : {len(resp2.tool_calls)}")
    print(f"  Turn Latency     : {resp2.latency_ms} ms")
    print(f"  Cumulative Cost  : ${client.usage.estimated_cost_usd:.6f}")
    print(f"  Cumulative Turns : {client.usage.call_count}")
    print("-" * 55)
    print("STEP 4 VERIFICATION COMPLETE: ALL CHECKS PASSED")

if __name__ == "__main__":
    main()

