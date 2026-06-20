# QuestAISecurity

企业 AI Agent 安全研究库：把 Agent 的工具、权限、数据、Skill、MCP、本地执行与业务自治风险，转化为可落地的架构、治理和 MVP 决策。

本仓库关注的不是“模型会不会答错”，而是：当 Agent 能读数据、调工具、写系统、运行命令、安装扩展并代表用户行动时，企业如何限制爆炸半径，并做到可审计、可回退、可治理。

## 内容地图

| 文档 | 适合解决的问题 |
| --- | --- |
| [企业 AI Agent 数据安全深度研究报告](<深度研究/企业 AI Agent 数据安全深度研究报告.md>) | 敏感数据、工具权限、连接器、MCP、审计与 Agent 数据安全防线 |
| [企业级 AI Agent Skill 安全研究报告](<深度研究/企业级 AI Agent Skill 安全研究报告.md>) | Skill 注册、签名、权限、沙箱、运行时策略、审计与产品化蓝图 |
| [构建本地 AI Agent 安全与隐私防护解决方案分析报告](<深度研究/构建本地AI Agent安全与隐私防护解决方案分析报告.md>) | 终端侧 Agent 发现、DLP、MCP/插件治理、命令与网络控制 |
| [企业部署 AI Agent 技术战略与首个垂直 Agent MVP 顶层设计研究](<深度研究/企业部署AI Agent技术战略与首个垂直Agent MVP顶层设计研究.md>) | 企业第一个垂直 Agent MVP 的场景选择、边界、验收与路线图 |
| [How we contain Claude across products](<案例收集/anthropic.com/how-we-contain-claude/how-we-contain-claude.md>) | Anthropic 的 Agent containment 实践：容器、沙箱、VM、egress control |
| [AI Agent 安全深度研究提示词模板](<提示词模板.md>) | 生成同类深度研究报告的结构化研究提示词 |

## 快速阅读路径

- 要评估企业 Agent 数据安全风险：先读数据安全报告。
- 要设计 Skill 安全平台：先读 Skill 安全报告。
- 要做终端侧本地 Agent 防护产品：先读本地 Agent 报告。
- 要规划第一个业务 Agent MVP：先读垂直 Agent MVP 顶层设计。
- 要扩展新的研究主题：从提示词模板开始。

## 核心判断

- Agent 安全的本质是 delegated authority security：谁把什么权限交给 Agent，权限如何被触发、滥用、放大和审计。
- Prompt 不是安全边界。最小权限、隔离环境、工具网关、动作审批、短效凭证和不可篡改日志才是底座。
- 不可信内容包括网页、邮件、文档、RAG 结果、工具返回、Skill metadata、插件配置和本地项目文件。
- 首个企业 Agent MVP 不应追求“大而全自治”，应选择高频、规则清晰、单线程、可验收、可回退的案件闭环场景。
- 好的 Agent 治理链路是：身份 -> 权限 -> 工具 -> 数据 -> 动作 -> 日志 -> 回滚。

## 仓库结构

```text
.
├── README.md
├── 提示词模板.md
├── 深度研究/
│   ├── 企业 AI Agent 数据安全深度研究报告.md
│   ├── 企业级 AI Agent Skill 安全研究报告.md
│   ├── 构建本地AI Agent安全与隐私防护解决方案分析报告.md
│   └── 企业部署AI Agent技术战略与首个垂直Agent MVP顶层设计研究.md
└── 案例收集/
    └── anthropic.com/how-we-contain-claude/how-we-contain-claude.md
```

## 维护原则

- 优先使用一手资料、官方规范、安全公告、标准文件和可验证案例。
- 明确区分事实、行业共识、策略推断和实施建议。
- 每篇研究都必须回答：风险是什么、防线放在哪里、谁负责、如何验收。
- 避免输出可直接滥用的攻击代码、绕过步骤或真实目标攻击流程。
- 保持结论导向：少堆概念，多给架构、清单、指标、路线图和取舍。

## 当前状态

这是一个研究与决策资料库，不是 SDK、框架或生产系统。当前未声明开源许可证；公开复用前建议补充 `LICENSE`。
