# test_tool_loop.py - unit test for the SDK backend in tool_loop.py.
# Uses a fake client: no API key, no internet, no cost. The SDK backend is
# never run live, because a real API key costs money beyond Claude Pro.
from types import SimpleNamespace
import tool_loop

def block(**fields):
    """A fake content block: block(type="text", text="hi").text gives "hi"."""
    return SimpleNamespace(**fields)

class FakeMessages:
    """Stands in for client.messages. Hands out the scripted responses one by
    one, and remembers what the loop sent each time, so the test can check it."""
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
    def create(self, **kwargs):
        self.calls.append(kwargs)          # remember what the loop sent
        return self.responses.pop(0)       # give the next scripted response

class FakeClient:
    """Stands in for the SDK client: has .messages.create(), like the real one."""
    def __init__(self, responses):
        self.messages = FakeMessages(responses)

def test_sdk_backend_runs_tool_then_answers():
    responses = [
        # Turn 1: Claude asks for list_ads
        SimpleNamespace(stop_reason="tool_use", content=[
            block(type="tool_use", id="toolu_test1", name="list_ads", input={})]),
        # Turn 2: Claude is done
        SimpleNamespace(stop_reason="end_turn", content=[
            block(type="text", text="TEST ANSWER")]),
    ]
    fake = FakeClient(responses)
    answer = tool_loop.run("sdk", fake)

    # The loop returned Claude's final answer, after exactly 2 calls
    assert answer == "TEST ANSWER"
    assert len(fake.messages.calls) == 2
    # In call 2, the last message is the tool result, labelled with the right id
    tool_result = fake.messages.calls[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "toolu_test1"
    assert tool_result["content"].startswith("number | score | title")

if __name__ == "__main__":
    test_sdk_backend_runs_tool_then_answers()
    print("OK - SDK backend test passed")