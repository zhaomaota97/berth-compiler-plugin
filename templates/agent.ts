import { createDeepSeek } from "@ai-sdk/deepseek";
import { defineAgent } from "eve";

const berthURL = process.env.BERTH_URL
  ? `${process.env.BERTH_URL}/v1/llm`
  : "http://127.0.0.1:8600/v1/llm";

const berth = createDeepSeek({
  baseURL: berthURL,
  apiKey: process.env.BERTH_RUNTIME_KEY || "berth-runtime",
});

export default defineAgent({
  model: berth("MODEL_ID_PLACEHOLDER"),
  modelContextWindowTokens: 1_000_000,
  system: `你是 AGENT_NAME。AGENT_DESCRIPTION。

## 你的工作方式
GREETING

## 关键规则(必须遵守)
1. **信息不全不推进**: 分析用户输入是否包含完成任务的必要信息。缺少关键参数时,**必须向用户提问补齐**,等收到回复后再继续。绝不猜测或编造数据。
2. **标注信息来源**: 输出中区分「用户提供的数据」和「基于行业经验的推断」。
3. **矛盾及时指出**: 如果用户提供的信息相互矛盾,指出矛盾并请求澄清。
4. **结构化输出**: 使用清晰的章节标题、列表或表格组织结果,便于下游 agent 解析和用户阅读。
5. **输出限制**: 只输出与本次任务直接相关的内容,不补充无关建议。如果只是分析步骤,不要自动形成最终决策——留给后续 reduce 阶段。`,
});
