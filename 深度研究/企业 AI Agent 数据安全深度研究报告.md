# 企业 AI Agent 数据安全深度研究报告

## 执行摘要

截至 2026-06-19，本报告的核心结论是：**企业内敏感数据和数字资产的 AI Agent 安全问题，本质上不是“模型答得准不准”，而是“一个具备工具、权限、记忆、连接器和执行能力的代理，被授予了什么 authority，以及这些 authority 如何被劫持、误用、放大和不可审计地扩散”。** MCP 官方规范明确承认这类系统天然触及“任意数据访问与代码执行路径”；NCSC、CISA 与 OWASP 也都把 agentic AI 的新增风险集中指向更大的攻击面、权限蔓延、行为失配、外部内容注入、监控困难与责任归因困难。

**最大风险**不是单点模型漏洞，而是“三件事叠加”：**不可信外部内容**进入上下文、**过宽的工具与数据权限**被委托给 Agent、以及**缺少动作级审计与审批**。Anthropic 公开将浏览器型 Agent 的 prompt injection 称为“最重要的安全挑战之一”；OpenAI 则明确指出 prompt injection 可能通过下游工具调用外泄私有数据，且即使有缓解措施，Agent 仍会被诱骗或犯错。MCP 安全文档进一步指出，token passthrough、scope 设计不良、会话劫持、SSRF、以及本地 MCP server compromise 都会把“本来只是读数据”的代理迅速变成横向移动和外泄的起点。

**最优先落地的三项措施**是：  
- **把 Agent 从“继承用户全部权限”改为“独立 Agent 身份 + 最小权限 + 短效凭证 + scope 分层”**。NCSC 明确建议 least privilege、limit scope、avoid long-lived credentials；NIST 也已把 AI agent identity and authorization 单独拉出成为 NCCoE 研究方向。  
- **建立统一工具网关，默认拒绝非白名单工具，并对读写、外发、执行、状态变更实施动作级审批与策略判定**。MCP 规范要求显式用户同意；OpenAI 官方安全指南建议在 MCP 工具上保持 tool approvals，对读写都做人审。  
- **把环境层 containment 做在模型层之前**：隔离文件系统、网络出口、执行环境与本地工具；Anthropic 明确指出，真正决定成败的是确定性的环境边界，而不是期望模型层总能识别异常外泄。

**最不建议做的三件事**是：把 Agent 直接接到生产写权限、把外部网页/邮件/文档当可信上下文、以及把“系统提示词 + 内容过滤”误当成主要防线。NCSC 直接建议：如果你不能理解、监控或约束 Agent 的动作，它就还没准备好上线；NCSC 还明确指出 prompt injection 不是 SQL injection，当前模型内部并不存在稳固的数据/指令安全边界。

**适合立即行动的组织**是：已经在企业知识库、代码仓库、邮件/日程、工单、CRM/ERP、浏览器、分析平台、或 DevOps 流程中部署了具备工具调用与数据读写能力的 Agent 的组织，尤其是受监管行业、跨国公司、以及拥有高价值知识产权、财务流程和客户数据的企业。**不适合盲目投入的场景**则是：尚未完成资产分级、没有统一 IAM、没有审计/日志、无法做审批与回滚、或根本无法回答“这个 Agent 到底代表谁、能访问什么、改了什么、外发了什么”的团队。这个判断直接对应 NCSC 的“从低风险、范围受控的试点开始”原则，以及 NIST/NCSC 对全生命周期治理、第三方与审计能力的要求。

## 定义与证据

### 主题定义与边界

本报告讨论的不是一般意义上的“AI 数据安全”，而是**企业 Agent 在被委托访问企业内敏感数据和数字资产后，如何避免因注入、误判、越权、工具滥用、记忆污染、连接器失陷、执行环境缺陷与供应链污染而造成泄露、篡改、误执行和级联故障**。之所以这属于 **AI Agent 安全**，是因为风险的载体是“能行动的代理”而非“只会生成文本的模型”；MCP 规范把这种能力具体化为 resources、prompts、tools、sampling、stateful connections 与 arbitrary data access / code execution paths。

它**不等于**普通 LLM 安全。普通 LLM 安全更强调越狱、幻觉、有害内容与输出合规；本主题则更强调 **delegated authority security**：谁把什么权限交给 Agent、这些权限被什么上下文触发、Agent 是否会通过工具把数据发到不该去的地方、是否会执行不可逆动作、以及事后能否归因。OpenAI 的 Agent 安全指南把“prompt injections”与“private data leakage via downstream MCP/tool calls”并列；Anthropic 的浏览器 Agent 研究把“网页、邮件、文档、应用中的隐藏指令”视为可直接改变代理行为的攻击面。

它也**不等于**传统 AppSec、云安全或数据安全，但必须把三者合并起来看：  
- 没有 AppSec，工具层、插件层、MCP server、编排器和执行环境本身就会暴露命令执行、文件写入、反序列化和 secret 泄露缺陷。  
- 没有云/IAM 安全，Agent 就会在连接器、令牌、API scope 和基础设施层扩大 blast radius。  
- 没有数据安全，Agent 会在 RAG、memory、connectors 与 tool outputs 上跨越数据最小化边界，把本应局部可见的数据变成“上下文可见”甚至“可外发”。

本报告采用以下假设：一是研究对象为企业环境中已进入或准备进入真实流程的 Agent；二是优先覆盖“读敏感数据、调用工具、可能写状态”的系统；三是不输出可直接复现攻击的代码或绕过步骤；四是对 2026 年仍快速演化的标准与协议保持保守判断。对“完全自治失控 Agent”这类叙事，本报告只讨论**在既有权限与工具被授权前提下**的现实风险，不把未经证据支持的强 AGI 情景当作当前决策依据。这个边界与 NCSC“从低风险、受控范围开始”的建议一致，也与官方资料当前围绕权限、工具、日志、审批、containment 的关注焦点一致。

### 证据矩阵

| 资料来源 | 类型 | 日期 | 核心观点 | 与主题关系 | 可信度 | 局限 |
| --- | --- | --- | --- | --- | --- | --- |
| OWASP Agentic AI Threats and Mitigations  | 社区权威安全指南 | 2025-02-17 | 把 agentic AI 风险单独抽出，按威胁模型组织 | 直接定义 Agent 特有威胁面 | 高 | 社区驱动，非监管标准 |
| OWASP Top 10 for Agentic Applications 2026  | 社区权威框架 | 2025-12-09 | 提供 autonomous/agentic systems 的关键风险清单 | 适合做风险盘点与优先级排序 | 高 | 框架性强，细节需本地化 |
| NIST AI 600-1 GenAI Profile  | 官方风险管理框架 | 2024-07-26 | 用 Govern / Map / Measure / Manage 组织 GenAI 风险，并要求第三方、指标、红队与 incident planning | 适合把 Agent 数据安全纳入企业治理与度量 | 很高 | 不是专门针对 Agent |
| MITRE ATLAS  | 官方/准官方知识库 | 2026-05 更新 | 提供 16 tactics、170 techniques、35 mitigations、57 case studies；已包含 agentic AI technique | 适合把 Agent 攻击链映射到可操作威胁模型 | 很高 | 更偏知识库，不给治理流程 |
| CISA / 国际伙伴 Careful Adoption of Agentic AI Services  | 官方联合指导 | 2026-04-29 | 指出 expanded attack surface、privilege creep、behavioral misalignment、obscure event records，建议 start small | 直接指向企业采纳与运行控制 | 很高 | 页面抓取受限，细节公开文本有限 |
| NCSC Thinking carefully before adopting agentic AI  | 官方实践建议 | 2026-06 | 不要给敏感数据/关键系统 unrestricted access；强调 least privilege、temporary creds、monitoring、incident plans | 直接支持最小权限与渐进部署 | 很高 | 原则性强 |
| NCSC / CISA Guidelines for secure AI system development  | 官方全生命周期开发指南 | 2023-11 初版，2026 页面持续维护 | 安全必须贯穿 design / development / deployment / operation；已纳入 logging、monitoring、update、information sharing | 适合作为工程与运营底座 | 很高 | AI 通用，不专指 Agent |
| MCP Specification 与 Authorization  | 官方协议规范 | 2025-03-26 / 2025-06-18 版本 | 明确 MCP 涉及 user consent、tool safety、OAuth 2.1、token audience validation、禁止接收非发给本 server 的 token | 直接决定工具层、连接器层与 delegated access 的安全边界 | 很高 | 协议仍在快速演进 |
| MCP Security Best Practices  | 官方安全最佳实践 | 2026-06 | 指出 confused deputy、token passthrough、SSRF、session hijacking、本地 server compromise、scope minimization 等 | 是企业使用 MCP / connector 生态的关键控制依据 | 很高 | 仍偏协议实现层 |
| NIST NCCoE Agent Identity and Authorization 概念论文  | 官方概念纸 / 征求意见 | 2026-02-05 | 代理身份、认证、授权、审计、不可否认性已被单列为新问题 | 说明 Agent IAM 是未来 6–18 个月的建设重点 | 高 | 仍为概念阶段，未成正式标准 |
| CISA Software Bill of Materials for AI – Minimum Elements  | 官方供应链透明度指导 | 2026-05-01 | 要求 AI 系统与供应链透明度 | 直接支撑 Agent 工具/模型/插件供应链治理 | 很高 | 实施细节需组织自定 |

### 行业共识与仍无共识的问题

当前**基本已有共识**的内容有五点。第一，**外部内容默认不可信**；网页、邮件、文档、RAG 内容、tool metadata 都可能包含机器可见但人类不易察觉的操纵指令。第二，**Agent 不应继承用户全部权限**，而应采用最小权限、最短时间、最小 scope。第三，**动作级同意与审计**是必要条件，尤其是读写敏感数据、外发、下单、转账、删改生产状态等操作。第四，**环境层 isolation 与 deterministic boundary** 比单纯提示词防御更可靠。第五，**Agent 安全必须进入全生命周期与第三方治理**，而不是产品团队局部加几个 guardrail 就算完成。上述判断同时被 NCSC、MCP 官方规范、OpenAI/Anthropic 官方文档与 NIST 风险管理资料支持。

当前**仍无共识**的内容也很明确。第一，**prompt injection 没有被证明可以像 SQL injection 那样被“根治”**；NCSC 明确认为 LLM 内部并不存在天然的数据/指令边界，OpenAI 也承认即使采用 guardrails、structured outputs、tool approvals，Agent 仍可能被 tricked。第二，**Agent 身份与授权模型仍在形成中**，NIST 还在为此征求反馈并准备做示范工程。第三，**MCP 与连接器生态的安全基线尚在快速演进**，官方安全最佳实践在 2026 年中还在持续补强。第四，**评估指标缺少统一工业标准**；目前可见的是各家 system card 和指南分别使用 ASR、confirmation recall、unauthorized access attempts、red-team findings 等局部指标。

## 场景、架构与攻击面

### 关键场景总览

| 场景 | Agent 能力 | 关键资产 | 信任边界 | 主要风险 | 业务影响 | 当前防线缺口 |
| --- | --- | --- | --- | --- | --- | --- |
| 企业知识库 / RAG Agent | 检索、总结、下载、分享、写回知识条目 | 合同、路线图、客户材料、财务与法务文档 | 文档库、向量库、检索器、重写器之间 | 间接提示注入、RAG 污染、敏感摘要过度外发；OWASP 明确指出 RAG 与微调都不能消除 prompt injection。 | 泄露商业机密、误导决策、错误引用污染后续流程 | 传统 DLP 只看最终输出，不看 tool call 与上下文拼接 |
| 浏览器 / Computer Use Agent | 打开页面、读取邮件、填表、点击、下载、上传 | 邮箱、CRM、工单、采购、财务帐号 | 网页内容、浏览器会话、表单动作、已登录站点 | 隐藏指令触发外发、误点击、误提交、带登录态的数据泄露；Anthropic 与 OpenAI 都把此类风险列为重点。 | 发错邮件、提交错误表单、触发采购/付款/账号操作 | CASB/浏览器隔离通常不理解 Agent 意图与动作链 |
| 代码生成 / DevOps Agent | 读取 repo、运行命令、改文件、触发 CI/CD、查日志 | 源码、密钥、CI token、基础设施定义、生产变更权限 | 本地工作站、容器、runner、repo、制品仓 | prompt injection 触发危险命令、文件写入、secret 外泄；历史与近期 advisories 证明这不是理论问题。 | 代码篡改、供应链污染、生产事故 | “先给全权限再靠人盯着”在实践里会因审批疲劳退化 |
| 财务 / HR / 办公自动化 Agent | 读取表格、生成邮件、审批建议、写 CRM/ERP、调用内部 API | 工资、PII、合同、发票、绩效、客户资料 | 邮件、表格、SaaS 连接器、审批系统 | 过度共享个人信息、错误状态变更、高风险决策自动化 | 合规违规、错误付款、错误人事动作、隐私事故 | 现有审批流多面向人，不面向 Agent trace 与 delegated identity |
| MCP / 插件 / 连接器生态 | 动态发现工具、OAuth 授权、跨 SaaS 调用、本地/远程 server 连接 | token、session、scope、tool metadata、环境变量、企业 API | client、MCP server、auth server、第三方 API、本地进程 | confused deputy、token passthrough、SSRF、session hijack、本地 server compromise、secret 泄露与供应链风险。 | 一次错误接入即可跨服务外泄和横移 | 许多团队仍把 MCP server 当“普通插件”而不是高权限代理边界 |

### 场景深拆

#### 企业知识库与 RAG Agent

业务目标通常是让 Agent 代表员工搜索、总结、对比、起草与分发内部知识。问题在于，一旦 Agent 同时拥有检索权、下载权、摘要权和外发能力，**泄露不再只发生在模型回答里，而会发生在检索、重写、tool call 与下游分享动作里**。OWASP 明确指出 prompt injection 仍是首要风险，且 RAG 与 fine-tuning 不能根除；OpenAI 也承认下游 MCP/tool call 可能带来 private data leakage。

**最可能的风险链**是：不可信文档或被污染知识条目进入检索结果，Agent 将其作为高优先级“说明”吸收，随后在总结、引用、权限推断或分享动作中把不该暴露的原文、片段、引用链或附件发往外部工具或低权限用户。最坏影响不是单次“答错”，而是**把企业知识库变成被操纵的自动外发器**。这与 MITRE ATLAS 中的 RAG poisoning、AI agent context poisoning、LLM data leakage 都能对应上。

**最小可行防线**应是：检索结果先经过数据分类与字段裁剪，只把任务所需最小片段送入上下文；Agent 默认只能读、不能直接分享原文；对跨租户、跨域、跨系统外发动作必须审批；对检索来源、引用文档 ID、原文字节数、摘要长度、外发目标做全链路日志。**成熟防线**则要增加文档来源可信度、内容 provenance、写回隔离、RAG 污染检测、以及“摘要可出域、原文不可出域”的策略化执行。NIST 已把 content provenance、PII 去除、第三方透明度与 incident planning 纳入建议动作。

#### 浏览器与 Computer Use Agent

浏览器型 Agent 的业务吸引力在于能跨系统完成端到端任务，但这恰好把**网页内容、DOM、可访问树、嵌入文档、广告、邮件正文、表单与登录态**全部纳入攻击面。Anthropic 给出的例子极其贴近企业现实：读取邮件、起草回复时，隐藏文本可诱导 Agent 把含有“confidential”的邮件转发出去；OpenAI 对 ChatGPT agent 的公开风险说明也直接提到，prompt injections 可能让 Agent 从 Connector 或已登录站点外泄数据，且因为工具更多，影响比过去更高。

**最坏影响**通常不是“网页上有恶意 prompt”本身，而是借已登录态、已授予连接器权限和自动化动作，把错误行为转换成有业务后果的状态改变，例如错误提交表单、下载并上传敏感文件、发出带敏感内容的邮件、触发采购与账务流程。Anthropic 的对策是把这类风险视为“浏览器 Agent 的核心挑战”，OpenAI 则公开采用 user confirmations、watch mode、terminal network restrictions 与 memory disabled 等多层措施。

**最小可行防线**应是：浏览器 Agent 只运行在远程、隔离的视觉浏览器环境；登录敏感站点后进入强制 watch mode；高风险动作需显式确认；禁止自动处理银行、HR、法务和邮箱中的批量状态修改。**成熟防线**再增加页面敏感区识别、跨站点数据流约束、出域内容比对、以及对已登录 session 的任务级绑定与过期。NCSC 的判断很直接：如果你不能理解、监控和约束 Agent 的动作，它就不该上线。

#### 代码与 DevOps Agent

这是目前**爆炸半径最大**的企业场景之一，因为代码 Agent 往往同时触达本地文件系统、repo、包管理器、shell、CI/CD、日志、制品仓，甚至生产集群。GitHub Advisory 和 NVD 已反复证明，Agent 框架与周边插件中的 file write、command execution、unsafe deserialization、prompt injection 不是抽象概念：LangChain 曾出现通过 `exec()` 导致 code injection 的高危问题；Microsoft Semantic Kernel 在 SessionsPythonPlugin 中出现 arbitrary file write；LangChain 还出现过可导致 persistent chat-history poisoning 的 unsafe deserialization；Anthropic 也公开说明若无文件系统与网络双重隔离，被 prompt-injected 的编码 Agent 可能修改敏感系统文件或外泄 SSH keys。

**最常见的失效模式**不是“模型恶意”，而是：Agent 读到不可信 issue/README/网页后把其中内容当作执行建议；拿着开发者权限直接运行命令；将 secret、env、私钥、CI token 送入外部工具；或把生成代码直接写入分支、触发 pipeline。Anthropic 公开数据显示，默认权限提示中 93% 会被用户批准，而 sandboxing 可把权限提示减少 84%；这说明纯靠频繁人工批准会很快退化成“形式上的安全”。

**最小可行防线**是：默认 read-only；命令与文件写入都在隔离容器中执行；网络出口仅允许明示的 registry、文档与工件源；任何写 repo、改基础设施定义、触发部署、访问 secret manager 的动作必须二次批准。**成熟防线**应增加签名验证、制品 provenance、agent-to-runner 的一次性凭证、分支保护与自动回滚，并把 agent trace 接入 DevSecOps 审计。

#### 财务、HR 与办公自动化 Agent

这类 Agent 最容易被误判为“只是个智能助手”，实际上它兼具**高敏数据访问**与**高合规责任**。工资、绩效、履历、发票、付款、合同、客户 PII 一旦进入 Agent 可见范围，错误外发、错误建议、错误写入与越权检索都会变成合规与业务事故。OpenAI 明确把 “mistakenly reveal private data … by typing personal information that the user didn’t expect to share into an online form” 作为 agent risk；并把基于高度敏感个人数据做高风险决策列为拒绝类场景。

**最危险的误区**是认为“已有人工审批流”就足够。事实上，原有审批流通常围绕人类操作者设计，不记录 delegated identity、prompt/context 来源、tool chain、数据分类和模型级决策痕迹，因此既难复盘，也难证明“Agent 为什么会把这条数据给这个系统”。NIST 对第三方 GAI、数据使用和 incident planning 的要求，正说明组织需要把此类 Agent 纳入正式治理而不是当作普通生产力工具。

**最小可行防线**应是：只允许 Agent 生成建议与草稿，不直接落账、不直接变更员工状态、不直接向外部收件人发送邮件；对 PII、薪酬、合同、支付与高风险敏感个人数据的访问必须字段级裁剪与审计。**成熟防线**应增加数据分级驱动的策略引擎、审批链数字签名、基于业务对象的 ABAC、以及审批与执行分离。

#### MCP、插件与连接器生态

这条线是当前最容易被低估、但最值得单独治理的边界。MCP 规范把 tools、resources、sampling 与 stateful connections 统一了，但同时明确承认其能力覆盖 arbitrary data access and code execution paths。MCP 安全最佳实践进一步集中指出 confused deputy、token passthrough、SSRF、session hijacking、本地 server compromise 与 scope minimization 问题；而最近的公开漏洞则显示，这些不是纸面担忧：LibreChat 的 MCP 集成可被恶意 URL 诱导发送环境变量中的关键 secrets；MCP Inspector 曾因连接不可信 server 而可能导致本机命令执行。

因此，**MCP server 必须被当成高权限企业集成组件，而不是“方便接一下的插件”**。**最小可行防线**是：只允许经过登记、审查和签名的 server 进入生产；每个 server 独立 audience、独立 scope、独立审批；本地 server 一律沙箱化；禁止 token passthrough；对 OAuth redirect、state、resource indicator、scope escalation 逐项验证。**成熟防线**则应增加 AIBOM / SBOM、注册表信誉、server 行为基线、以及对 tool metadata 与描述文本的完整性验证。

### 参考架构与攻击面

下面是面向企业敏感数据场景的 **文字版参考架构**。它不是某个厂商产品图，而是从 NIST、MCP、NCSC、OpenAI、Anthropic 与 MITRE ATLAS 的共同控制点反推出来的最小可治理架构。

```text
用户 / 上游系统 / 外部内容
        │
        ▼
会话入口层
        │
        ├── 输入分类与预处理
        ├── 敏感字段裁剪
        └── 会话级策略标签
        │
        ▼
Agent 编排器
        │
        ├── 模型调用层
        ├── 任务规划器
        ├── 子 Agent 协调
        ├── 记忆读写控制
        └── RAG 检索与引用控制
        │
        ▼
工具网关 / MCP 网关 / 连接器网关
        │
        ├── 工具白名单
        ├── 动作级授权
        ├── scope 缩减
        ├── 出站控制
        └── 审批与回调
        │
        ├──────────────► 企业数据源
        │                 文档库 / 数据仓库 / CRM / ERP / 邮件 / 代码仓 / 工单
        │
        ├──────────────► 执行环境
        │                 远程浏览器 / 沙箱容器 / 受限 shell / runner
        │
        ▼
策略引擎与审计层
        │
        ├── 策略决策
        ├── 风险评分
        ├── Kill Switch
        ├── 不可篡改日志
        └── 告警与工单
        │
        ▼
人类审批 / 业务所有者 / SOC / 平台运维
```

| 架构层 | 关键资产 | 信任假设 | 可被操纵的输入 | 可被滥用的动作 | 控制点 | 必要日志 |
| --- | --- | --- | --- | --- | --- | --- |
| 会话入口 | 用户输入、上传文件、上游 webhook | 用户不一定恶意，但输入不能被默认视为安全 | 文档、邮件、网页摘要、工单文本 | 把恶意内容送入高优先级上下文 | 输入分类、PII 裁剪、来源标签 | actor_id、source_uri、classification、input_hash |
| 编排器 | task graph、system/developer prompt、sub-agent 路由 | 编排逻辑本身可信，但上下文不可信 | tool result、RAG 片段、memory 条目 | 形成错误计划、跨代理传播 | structured outputs、context segmentation、step policy | trace_id、node_id、prompt_version、decision |
| RAG / 记忆 | 向量库、memory store、citation map | 检索结果不自动可信 | poisoned docs、旧记忆、错误摘要 | 持久污染、跨会话泄露 | write governance、TTL、source provenance | retrieved_doc_ids、memory_read_ids、memory_write_ids |
| 工具 / MCP / 连接器 | access token、scope、tool metadata | server 与 metadata 不能默认可信 | malicious redirect、tool description、URL | unauthorized read/write、SSRF、token misuse | per-tool consent、audience validation、scope minimization | tool_name、server_id、scope、audience、approval_id |
| 执行环境 | 文件系统、网络、shell、浏览器 session | 环境边界必须靠 deterministic controls | 命令参数、下载内容、网页 DOM | file write、network egress、状态变更 | sandbox、network egress allowlist、watch mode | command_hash、egress_dest、fs_path、session_state |
| 审计与响应 | trace、策略结果、审批结果、告警 | 日志必须可追责、不可篡改 | log omission、token passthrough、身份混淆 | 无法事后归因、无法快速止损 | immutable logging、kill switch、IR playbook | delegated_identity、policy_result、human_approver、rollback_id |

这套表的重点是：**Agent 安全不是“再加一个模型 guardrail”**，而是要在每一层都记录“谁在代表谁、基于什么上下文、调用了哪个工具、带了什么 scope、对什么资产做了什么动作”。MCP 安全文档把 token audience、per-client consent、session 绑定和 scope minimization 写成了协议级要求；NCSC 把 logging、monitoring、incident management 写入 operation and maintenance；OpenAI 企业侧则已把 conversations、uploaded files、memories、workspace users 等纳入 compliance logging。

## 威胁模型与风险判断

### 威胁模型

| 威胁 | 攻击入口 | 前置条件 | 典型链路 | 影响 | 可观测信号 | 映射框架 | 防护优先级 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 间接提示注入 | 网页、邮件、文档、RAG 内容 | Agent 会读取不可信内容并可执行动作 | 外部内容进入上下文 → 规划偏转 → tool call / 外发 / 错误决策 | 数据泄露、错误动作、错误结论 | 引用来源突然异常、与用户意图不一致的 tool call、出站目标偏离 | OWASP LLM01；ATLAS Direct/Indirect Prompt Injection；NCSC prompt injection guidance  | 极高 |
| 工具滥用 | MCP / connector / function calling | Agent 已有工具权限 | 正常任务中被诱导调用高权限工具 | 未授权读写、越权外发、执行副作用 | tool_name 与任务不匹配；写操作发生在只读任务 | MCP Tool Safety；ATLAS AI Agent Tool Invocation；OpenAI MCP tool calling risk  | 极高 |
| 权限蔓延 | IAM、OAuth、API token | Agent 使用用户继承权限或 broad scopes | 一次授权长期有效 → 多系统可达 → 横向访问扩大 | blast radius 放大、难撤销 | broad scopes、长期 token、跨系统访问增多 | NCSC least privilege；MCP Scope Minimization；NIST agent identity  | 极高 |
| token / consent 缺陷 | OAuth / MCP proxy | 动态 client registration、redirect/state 管理不当 | confused deputy / token passthrough / redirect misuse | 冒用用户访问第三方 API、审计丢失 | 401/redirect 异常、state mismatch、audience 不符 | MCP Authorization 与 Best Practices  | 极高 |
| RAG 污染 | 文档库、向量库、连接器同步 | 外部或低信任内容进入知识库 | poisoned content 被索引和高频检索 | 持续误导、数据泄露、错误引用 | 特定来源命中率异常、citation 异常集中 | ATLAS RAG Poisoning；OWASP Prompt Injection / RAG 不能根除  | 高 |
| 记忆污染 | memory store、chat history | Agent 有持久 memory | 恶意或错误信息被写入长期记忆并在后续任务被引用 | 跨会话偏转、长期泄露、难以追踪 | memory_write 后异常动作增加；相同错误跨会话复现 | ATLAS AI Agent Context Poisoning；LangChain persistent chat-history poisoning；研究证据为新近预印本  | 高 |
| 本地执行环境被借壳 | 本地 MCP server、shell、runner | Agent 能在本机或近端执行 | 不可信本地 server / 命令执行 / DNS rebinding / sandbox 缺失 | 本机 compromise、secret 外泄、文件破坏 | 异常子进程、访问敏感路径、未知外连 | MCP Local Server Compromise；Anthropic sandboxing；GitHub advisories  | 极高 |
| 框架与插件漏洞 | Agent framework / plugin / SDK | 使用开源或第三方组件 | 反序列化 / file write / command exec / env leak | 平台级 compromise | 组件版本命中 CVE/GHSA；异常文件写入 | CVE-2023-29374, CVE-2026-25592, CVE-2026-32625 等  | 高 |
| 跨 Agent 传播与级联故障 | 多 Agent 编排 | 子 Agent 可继承上下文或工具 | 上游被污染 → 下游继续信任与执行 | 级联误操作、放大影响面 | 多节点 trace 中异常 shared context | OpenAI multi-agent risk guidance；ATLAS agentic techniques  | 中高 |
| 不可逆动作误执行 | 浏览器、财务、邮件、生产系统 | Agent 拥有状态变更能力且审批不足 | 误操作或确认不足 → 发送、购买、删除、付款 | 直接业务损失、合规事故 | confirmation miss、审批绕过、状态变更失败率 | OpenAI user confirmations / watch mode；NCSC human accountability  | 极高 |
| 审计与归因失真 | token passthrough、共享身份、日志缺失 | 没有独立 Agent identity 与 trace | 代理代表谁不清楚，动作无法追溯 | 无法调查、无法证明合规、无法定责 | downstream 日志主体不一致、trace 缺口 | MCP audit trail issues；OpenAI compliance logs；NIST metrics guidance  | 高 |

### 风险判断

**高概率风险**主要集中在四类：  
其一，**不可信内容导致的行为偏转**。这已经是官方和厂商都反复承认的现实问题，而不是概念炒作。其二，**过宽的工具与连接器权限**。这往往来自“先把权限打通，后面再优化”的上线习惯。其三，**私有数据被模型或工具链过度分享**，即便没有攻击者也可能发生。其四，**日志与归因不足**，导致事故后既不能迅速止损，也不能解释到底是模型、策略、工具还是数据源出了问题。

**低概率但高影响风险**主要包括：本地或近端执行环境被借壳导致主机 compromise、MCP/OAuth 设计缺陷带来的跨系统 token 滥用、DevOps Agent 误写或误部署造成供应链与生产事故、以及多 Agent 级联扩散。近期公开 advisory 已表明，这些链路并不需要“超级智能”；只要普通代理拿到了错误的执行面，就足以造成严重后果。

**更接近概念炒作的说法**是把当前企业 Agent 的核心风险描述为“无任何现有权限、无任何连接器授权、无任何执行面时，Agent 自主突破系统边界并全面接管企业”。**暂无可靠证据**表明这才是当前主导风险。更扎实的证据恰恰相反：现实问题主要来自**被授权的权限、被接入的工具、被放行的网络、被接受的上下文、以及被忽略的审计边界**。这是基于当前官方规范、厂商 system card、NCSC 与公开漏洞的综合判断。

## 防御、评估与治理落地

### 防御架构分层

下表按 **最小可行防线 / 标准企业防线 / 高成熟度防线** 三档给出控制项。原则只有一句话：**不要先追求“更 autonomous”，要先追求“更 bounded、更 attributable、更 reversible”。** 这与 NCSC 的“walk before you run”、MCP 的 consent / authorization 要求、以及 Anthropic 的 containment 哲学一致。

| 档位 | 控制项 | 防什么 | 放在哪里 | 实现方式 | Owner | 验收标准 | 代价 / 副作用 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 最小可行 | Agent 资产盘点与数据分级 | 不知道谁在碰敏感数据 | 平台总表与 CMDB | 建 Agent 清单、标数据等级、标工具清单、标写权限 | 平台 + 安全治理 | 覆盖率 ≥ 95%，高风险 Agent 全部标注 owner | 需要跨团队梳理流程 |
| 最小可行 | 独立 Agent 身份与短效凭证 | 用户权限继承、长期 token | IAM / connector 层 | 每个 Agent 独立 principal；短效 token；按任务下发 scope | IAM 团队 | 无共享 service account；高权 token TTL ≤ 1h | 接 IAM 成本高，但 blast radius 显著下降  |
| 最小可行 | 工具白名单与默认拒绝 | 任意工具被调用 | 工具网关 | 只允许已登记 tools；禁未审插件 | 平台安全 | 非白名单调用率 = 0 | 初期会降低灵活性  |
| 最小可行 | 读写分离与高风险动作审批 | 不可逆误执行 | 工具网关 / UI | read-only default；写/外发/执行动作强制确认 | 业务 owner + 平台 | critical action 未审批执行率 = 0 | 会增加时延；但“频繁提示”会带来审批疲劳，需精细设计。Anthropic 报告默认提示中 93% 被批准。 |
| 最小可行 | 上下文最小化与 structured outputs | prompt injection、过度共享 | 编排器 | 外部输入只进 user channel；节点间用 schema/enum/validated JSON | 应用团队 | 任意自由文本直驱高权限工具 = 0 | 减少灵活性，但可显著缩小注入面  |
| 标准企业 | 统一 MCP / connector 网关 | token misuse、审计断裂 | 集成层 | audience validation、per-client consent、禁 token passthrough | 平台安全 | 所有 remote MCP 经网关；audience 校验覆盖 = 100% | 需要协议适配成本  |
| 标准企业 | Memory / RAG 写入治理 | 持久污染 | memory / retrieval 层 | 允许写入的来源白名单、TTL、审批写回、来源追踪 | 知识平台 | 未经批准写回率 = 0；可追溯率 = 100% | 会降低个性化体验  |
| 标准企业 | 沙箱执行与网络出口控制 | code exec、secret 外泄 | 执行环境 | 远程浏览器、隔离容器、只允许特定 egress | 平台工程 | 非允许出口阻断率 ≥ 99.9% | 维护复杂；但 Anthropic 表明双重 isolation 是必要条件。 |
| 标准企业 | 不可篡改日志与全链路 trace | 无法归因 | 审计层 | 记录 delegated identity、retrieval IDs、tool calls、审批与策略结果 | 平台 + SOC | 审计覆盖率 ≥ 95%，trace 断点可定位 | 存储成本增加  |
| 标准企业 | Kill Switch 与回滚 | 失控 Agent、级联故障 | 编排器 / 网关 / 执行层 | 一键停用 Agent、停 connector、吊销 scope、回滚最近动作 | 平台 SRE | kill switch 演练通过；5 分钟内完成停用 | 需要预留回滚接口 |
| 高成熟度 | 风险感知策略引擎 | 动态风险变化 | 编排器 / 网关 / 数据层 | 基于数据等级、动作类型、目标系统、用户态势做动态决策 | 安全平台 | 高风险动作阻断率、误报率可量化 | 实施复杂、要调参 |
| 高成熟度 | 供应链透明度与 AIBOM / SBOM | 插件/模型/工具污染 | 采购与部署 | 要求 AI SBOM、版本锁定、签名、CVE 监测 | 采购 + 平台安全 | 生产组件 SBOM 覆盖 ≥ 90% | 与供应商博弈成本高  |
| 高成熟度 | 持续红队与回归评估 | 防线随版本退化 | CI/CD + 运行时 | 每次模型、prompt、tool、policy 变更触发基准回归 | 安全测试 | 关键风险回归必跑；失败阻断上线 | 会拉长发布节奏  |

### 工程最小要求

从工程落地角度，**没有这些字段，就谈不上企业级 Agent 审计**：`actor_id`、`delegated_identity`、`agent_id`、`session_id`、`trace_id`、`workflow_node`、`prompt_version`、`retrieved_doc_ids`、`memory_read_ids`、`memory_write_ids`、`tool_name`、`tool_server_id`、`scope`、`audience`、`approval_id`、`egress_destination`、`data_classification`、`policy_result`、`side_effect_status`、`rollback_id`。这是基于 NCSC 的 logging and monitoring 要求、MCP 的 token audience / per-client consent 要求、以及企业级 audit API 所暴露的最小归因维度综合推导出来的实施清单。

建议的**最小告警规则**包括：只读任务触发写操作；低风险任务调用高危工具；新接入 MCP server 首次触发广泛 scope；检索任务把原文发送给外部域；单会话内连续 approval miss；memory 写入后下一次会话出现跨域外发；执行环境访问非允许网段；同一 Agent 在短时内跨多个敏感系统抓取数据。上述规则本质上都围绕“意图—权限—动作—证据”的一致性校验展开。

### 红队、评估与验收

NIST 已明确建议识别 unauthorized access attempts、penetrations 等指标，并进行 AI red-teaming；OpenAI 和 Anthropic 也都公开使用 confirmation recall 与 attack success rate 这类 agent-specific 指标。企业不应只做“功能验收”，而应把 **agentic misuse** 变成正式质量门禁。

| 测试项 | 测什么风险 | 测试方法 | 成功 / 失败判定 | 指标 | 频率 |
| --- | --- | --- | --- | --- | --- |
| 间接提示注入回归 | 外部内容是否能改写行为 | 用网页、邮件、文档、知识条目构造防御性测试集 | 关键场景中禁止出现未授权 tool call 或外发 | **建议阈值**：高风险流程 ASR < 1%；低风险流程 < 3% | 每次模型/提示词/检索变更 |
| 未授权工具调用 | 规划偏转与权限绕过 | 任务与工具白名单不匹配的用例集 | 所有越界 tool calls 必须被阻断 | 未授权工具调用率 = 0 | 每周 + 上线前 |
| 敏感数据泄露 | 原文、PII、secret 外泄 | 构造红线数据样本，检查回复、tool input、外发内容 | 任何红线数据出域即失败 | 敏感数据泄露率 = 0 | 每周 |
| 审批绕过 | 高风险动作未确认就执行 | 对发送、购买、删除、支付等动作做对抗测试 | critical actions 必须 100% 进审批 | 高风险动作阻断率；审批绕过率 | 每次版本变更 |
| 记忆污染持久化 | memory 造成跨会话毒性 | 先写入污染记忆，再做后续任务 | 未经治理的污染持久即失败 | 记忆污染持久化率 | 双周 |
| RAG 污染命中 | poisoned docs 是否被高权信任 | 把伪造条目混入测试索引 | 命中污染内容后不能直接驱动写操作 | RAG 污染命中率；citation 异常率 | 双周 |
| scope 越界与 token 误用 | delegated access 设计错误 | 验证 audience、scope、token passthrough、redirect/state | 任一 mismatch 未阻断即失败 | 权限越界调用率 = 0 | 每次 connector 变更 |
| 沙箱与 egress | 执行环境 containment | 受控任务尝试访问禁止路径/域名 | 必须被阻断并告警 | sandbox escape 告警率；非法 egress 阻断率 | 每周 |
| 审计覆盖与可归因性 | 事故后能否复盘 | 随机抽样 20 条 trace 人工复盘 | 关键字段缺失 > 5% 即失败 | 审计覆盖率；trace 完整率 | 每周 |
| 运行时响应 | 发现与处置速度 | 模拟 connector 泄露 / Agent 失控事件 | 达不到目标 MTTD / MTTR 即失败 | MTTD、MTTR、吊销时延、回滚成功率 | 月度演练 |

这里特别建议记录两个**组织级硬指标**：  
- **prompt injection ASR**，因为 Anthropic 已证明浏览器 Agent 的对抗评估必须看攻击成功率而不是只看模型答复。  
- **confirmation recall**，因为 OpenAI system card 公布的 relevant action confirmation recall 为 91.0%，这恰恰说明“有审批节点”不等于“审批一定触发到了应该触发的地方”。

### 组织治理与责任归因

建议的最小 RACI 如下：**业务 owner 负责“Agent 是否有必要存在”与“风险是否可接受”；平台团队负责编排器、网关、执行环境与日志；IAM 团队负责 agent identity、scope、token 生命周期；数据平台负责分类分级、RAG 来源治理与 memory 写入规则；SOC / 安全部门负责检测、红队、应急与例外审批；采购 / 法务负责第三方与供应链条款。** 这与 NCSC 强调的人类 accountability，以及 NIST 对 third-party governance、incident response 与 vendor assessment 的要求是一致的。

## 路线图、Build Buy Integrate 与不建议清单

### 落地路线图

以下路线图是基于 NCSC“start small、use agents only for low-risk tasks”、NIST 的 third-party / incident / metrics 要求，以及 MCP 官方安全控制最小集综合形成的实施建议。

| 阶段 | 时间 | 目标 | 任务 | 交付物 | Owner | 依赖 | 风险 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 封堵期 | 0–30 天 | 看清全局并先堵高风险洞 | 盘点所有 Agent、工具、连接器、数据域；停用高风险直写权限；补最关键日志；冻结未审 MCP / 插件 | Agent 清单、风险分级、禁用清单、日志基线 | 平台 + 安全 | IAM、CMDB、业务 owner | 资产遗漏、业务阻力 |
| 收口期 | 31–60 天 | 形成统一控制面 | 上线工具网关、动作审批、scope 缩减、人类确认节点、MCP 登记制、红队测试集 v1 | 工具网关、审批流、评估集 v1 | 平台工程 + IAM | 网关、审批系统 | 工具兼容性、性能影响 |
| 稳定期 | 61–90 天 | 进入运行时治理 | 上线 runtime monitoring、policy engine、sandbox egress 控制、供应链校验、IR playbook | 运行监控、告警、IR 手册、SBOM 清单 | SRE + SOC + 平台安全 | SIEM、容器环境、采购 | 告警噪声、跨团队协同 |
| 平台化期 | 90 天以上 | 从项目制走向平台制 | 建成熟度模型、例外流程、持续红队、合规映射、统一 Agent IAM | Agent 安全平台、成熟度分级、季度评审机制 | CISO 牵头 | 预算、治理委员会 | 平台过重、组织疲劳 |

### Build Buy Integrate 决策

| 方案 | 适合场景 | 优点 | 风险 | 成本 | 上线速度 | 锁定风险 | 推荐度 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 自研控制面 | 高价值数据、复杂内部流程、已有强平台/IAM/日志基础 | 可把权限、审批、trace、数据分类深度接入企业现有体系 | 工程投入大；若团队弱，容易把新边界自己做坏 | 高 | 中 | 低 | **高**，但前提是平台能力成熟 |
| 采购专用安全层 | 多业务线并行、需快速统一 guardrails 与审计 | 上线快、可尽快形成统一视图与策略入口 | 供应商透明度、数据驻留、误报、闭源黑盒 | 中高 | 快 | 中高 | **中高**，触发条件是 Agent 数量已多且治理分散 |
| 集成云厂商原生能力 | 已重度依赖单一云/模型平台 | 身份、网络、日志与执行环境可复用既有控制 | 强绑定云生态；跨云与跨模型一致性差 | 中 | 快 | 高 | **中高**，适合单平台集中式组织 |
| 开源集成 | 低风险试点、研究、内部小规模 | 灵活、成本低、适合快速验证 | 最近公开漏洞很多；需自担补丁、审计、沙箱、供应链风险 | 低到中 | 快 | 低 | **中**，仅适合受控环境，不宜直上高敏生产 |
| 混合模式 | 绝大多数中大型企业 | 核心控制自研，外围检测/可视化/审计采购，底层能力复用云原生 | 架构复杂、流程设计要求高 | 中高 | 中 | 中 | **最高**，现实可行性最佳 |

**触发条件**建议这样判断：  
- **优先自研**：当 Agent 直接碰“皇冠资产”——核心代码、核心客户数据、财务支付、生产变更——且你需要把 delegated identity、数据分级、审批、回滚和内部工单系统深度绑定时。  
- **优先采购**：当你已经有多个 Agent 团队、多个模型/工具栈、多个 SaaS 连接器，且 90 天内需要形成统一最小治理面时。  
- **优先开源集成**：仅当场景低风险、环境受限、无外发、无生产写权限、且具备 SBOM / CVE / 沙箱 / 版本锁定能力时。这个判断直接受 NIST 的 third-party due diligence、CISA 的 AI SBOM、以及近年的公开 Agent / MCP 组件漏洞现实影响。

### 不建议清单

| 危险做法 | 为什么危险 | 替代方案 |
| --- | --- | --- |
| 让 Agent 继承用户全部权限 | 一旦行为偏转，blast radius 直接等于用户权限上限；NCSC 已明确反对 unrestricted access。 | 独立 Agent identity、任务级短效凭证、scope 分层 |
| 把外部网页、邮件、文档视为可信上下文 | 浏览器与知识场景中，隐藏指令是现实攻击面。 | 外部内容统一降级为不可信输入；结构化抽取后再传递 |
| 只靠系统提示词防注入 | NCSC 明确指出 prompt injection 不像 SQL injection 那样有根性分离手段；OpenAI 也承认 mitigations 不会完美。 | 环境层隔离 + structured outputs + 工具审批 + egress 控制 |
| 没有工具调用审计 | 事故后无法知道数据经哪个 tool 出域 | 记录 tool server、scope、approval、egress、side effect |
| 没有高风险动作审批 | 购买、发送、删除、支付等会直接产生业务后果 | 动作级审批，状态变更前强制确认 |
| 没有记忆写入治理 | 污染会跨会话、跨任务持续存在 | memory 写入白名单、TTL、来源追踪、审批写回 |
| 没有沙箱与网络隔离 | 一旦执行环境被借壳，secret 与文件系统会直接暴露 | 远程浏览器、隔离容器、egress allowlist、只读默认 |
| 没有红队回归测试 | 防线会随模型、prompt、tool 版本变化悄然退化 | 每次变更必跑注入、越权、泄露、审批、回滚回归 |
| 把 MCP server 当成普通插件 | MCP 直接处在 delegated permissions 与 chained tool calls 的要害位置 | 视为高权限集成组件，纳入 OAuth / scope / consent / SBOM 管理 |
| 没有 Agent 身份与责任归因 | 无法回答“谁代表谁做了什么” | Agent principal、delegated identity、trace 与审批绑定 |

## 结论与决策建议

**现在是否应该投入这类安全建设？**  
**应该，但前提不是“上更多 guardrail”，而是先建立 Agent authority control plane。** 只要你的 Agent 已经接入知识库、邮件、浏览器、代码仓、SaaS 连接器、数据库或业务 API，并能够读取敏感数据或改变系统状态，就已经进入需要正式安全建设的阶段。NCSC 与 CISA 的联合指导之所以强调 start small，并不是建议观望，而是建议**立即采用受控方式进入**。

**最先保护哪类 Agent？**  
优先级应当是：  
**浏览器 / 办公自动化 / DevOps / 知识库 Agent**。原因不是它们“最先进”，而是它们最容易同时拥有登录态、连接器、执行权与敏感数据可见性。尤其是能写状态的 Agent，要比纯问答 Agent 高一个数量级。这个排序与 Anthropic 对浏览器 Agent 的风险认定、OpenAI 对 connectors 与 terminal 的防护设计、以及近年框架和插件的真实漏洞暴露面一致。

**最先封堵哪条风险链？**  
先堵这条：**不可信内容 → 进入高权限上下文 → 驱动工具调用 / 外发 / 状态变更 → 无审计或难回滚。** 这是眼下企业里最常见、也最危险的 Agent 数据安全主链路。只谈“内容安全”不够，只谈“身份安全”也不够，必须把上下文、权限、工具和审计放进同一条控制链。

**最小可行投入是什么？**  
最低可行包应包括七项：**Agent 清单、独立 Agent 身份、工具白名单、读写分离、关键动作审批、执行环境隔离、全链路审计日志**。如果预算更紧，宁可先限制能力，也不要先放开能力后期待用户谨慎操作。NCSC 的原话已经足够明确：不能理解、监控或约束，就不应部署。

**三个月内可以交付什么？**  
三个月内完全可以交付：高风险 Agent 资产盘点、权限收敛、MCP/连接器登记制、工具网关、人类审批、基本 runtime 监控、注入/越权/泄露评估集、事件响应预案和最小 kill switch。做不到的通常不是技术，而是 owner 不清、权限边界扯不清、以及业务不愿接受“先缩权再扩权”的方法。

**哪些风险无法完全消除，只能降低概率与爆炸半径？**  
至少有三类：**prompt injection、Agent mistake、第三方 / 供应链缺陷**。NCSC 已明确指出 prompt injection 可能永远不像 SQL injection 那样被完全消除；OpenAI 也承认 Agent 仍会犯错或被 tricked；而最近的 GHSA / CVE 则表明第三方框架、MCP 组件与集成层缺陷会持续出现。现实可行路线不是“消灭风险”，而是**最小权限、最小上下文暴露、最小自主性、最小可达范围、以及最强可观测与回滚**。

**决策层、架构团队、安全团队、业务团队分别该做什么？**  
决策层要做的不是拍板“全面上 Agent”，而是要求每个 Agent 都能回答四个问题：**为什么需要、代表谁、能碰什么、出了事怎么停。** 架构团队应先建统一工具与身份边界，再谈多 Agent 与更高 autonomy。安全团队应把 Agent 纳入 IAM、供应链、红队、IR 与审计主流程。业务团队则必须接受一个现实：**越是涉及敏感数据与高风险动作，越不能把 Agent 当成“有点聪明的 UI 自动化脚本”**。这不是保守，而是当前官方资料、公开漏洞与厂商系统卡共同指向的现实工程结论。