import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import research_agent  # noqa: E402


ENV_NAMES = [
    "LLM_BASE_URL",
    "LLM_API_KEY",
    "LLM_MODEL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_MODEL",
]


def assert_true(condition, message, detail=None):
    if not condition:
        raise AssertionError(json.dumps({
            "message": message,
            "detail": detail,
        }, ensure_ascii=False, indent=2))


def with_env(values):
    previous = {name: os.environ.get(name) for name in ENV_NAMES}
    for name in ENV_NAMES:
        os.environ.pop(name, None)
    os.environ.update(values)
    return previous


def restore_env(previous):
    for name in ENV_NAMES:
        if previous.get(name) is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous[name]


def check_anthropic_config_and_request_shape():
    previous = with_env({
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "ANTHROPIC_BASE_URL": "https://api.anthropic.com/v1",
        "ANTHROPIC_MODEL": "claude-test-model",
        "LLM_BASE_URL": "https://legacy.example/v1",
        "LLM_API_KEY": "legacy-key",
        "LLM_MODEL": "legacy-model",
    })
    captured = {}
    original_http_json = research_agent.http_json

    def fake_http_json(url, headers, payload=None, timeout=6.0):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload
        captured["timeout"] = timeout
        return {"content": [{"type": "text", "text": "{\"ok\": true}"}]}

    try:
        research_agent.http_json = fake_http_json
        assert_true(research_agent.llm_configured(), "ANTHROPIC_API_KEY 应被识别为可用模型配置")
        result = research_agent.call_llm_json([
            {"role": "system", "content": "只输出JSON"},
            {"role": "user", "content": "{\"ping\": true}"},
        ])
    finally:
        research_agent.http_json = original_http_json
        restore_env(previous)

    assert_true(result == {"ok": True}, "Anthropic 响应正文应能按 JSON 解析", result)
    assert_true(captured.get("url") == "https://api.anthropic.com/v1/messages", "Claude/Anthropic 应调用 Messages API", captured)
    assert_true(captured.get("headers", {}).get("x-api-key") == "test-anthropic-key", "Anthropic 请求应使用 x-api-key", captured)
    assert_true(captured.get("headers", {}).get("anthropic-version"), "Anthropic 请求应声明 API version", captured)
    payload = captured.get("payload") or {}
    assert_true(payload.get("model") == "claude-test-model", "Anthropic 请求应使用 ANTHROPIC_MODEL", payload)
    assert_true(payload.get("system") == "只输出JSON", "system 消息应映射到 Anthropic system 字段", payload)
    assert_true(payload.get("messages") == [{"role": "user", "content": "{\"ping\": true}"}], "Anthropic messages 不应包含 system role", payload)


def check_legacy_openai_compatible_config_still_works():
    previous = with_env({
        "LLM_BASE_URL": "https://legacy.example/v1",
        "LLM_API_KEY": "legacy-key",
        "LLM_MODEL": "legacy-model",
    })
    captured = {}
    original_http_json = research_agent.http_json

    def fake_http_json(url, headers, payload=None, timeout=6.0):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload
        return {"choices": [{"message": {"content": "{\"legacy\": true}"}}]}

    try:
        research_agent.http_json = fake_http_json
        result = research_agent.call_llm_json([{"role": "user", "content": "{}"}])
    finally:
        research_agent.http_json = original_http_json
        restore_env(previous)

    assert_true(result == {"legacy": True}, "旧 OpenAI 兼容配置仍应可用", result)
    assert_true(captured.get("url") == "https://legacy.example/v1/chat/completions", "旧配置应继续调用 chat/completions", captured)
    assert_true(captured.get("headers", {}).get("Authorization") == "Bearer legacy-key", "旧配置应继续使用 Bearer key", captured)


def main():
    check_anthropic_config_and_request_shape()
    check_legacy_openai_compatible_config_still_works()
    print(json.dumps({"ok": True, "checked": ["anthropic_config", "legacy_openai_compatible_config"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
