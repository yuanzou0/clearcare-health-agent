# Governed Agent Lab / 可治理智能体实验平台

[English](README.md) | [简体中文](README.zh-CN.md)

这是一个围绕**有界、可评估、可治理 AI Agent**构建的工程与产品作品集。仓库将
白名单 Agent Runtime、受控证据、与 Provider 无关的评测、失败分析和可复用
Codex Skills 组合为一套可以持续验证的系统。

**ClearCare Health / 澄心循证健康智能体是第一个已经实现的参考垂直场景，不再是
整个平台的品牌。** 当前网页、安全路由、知识库和实测结论仍然属于健康场景。
跨领域 Adapter 和第二个垂直案例属于路线图，不能描述成已经完成。

> [!WARNING]
> 健康演示仅用于研究和教学，不提供诊断、处方或治疗建议，也不能替代医生。
> 不要输入真实患者姓名、证件、联系方式或其他敏感信息。

## 当前实现状态

| 层级 | 当前状态 |
|---|---|
| 有界 Agent Runtime | 已实现：单次规划—工具—回答循环；动作与原因组合使用白名单；最多一次只读工具调用 |
| 受控证据 | 已在 ClearCare 实现：来源注册表、出处、复核日期、域名绑定、时效性和 SHA-256 校验 |
| Evaluation | 已实现：确定性与 Provider 无关的案例、隐私安全预测记录、失败分类、Keyword/BM25 对照 |
| 模型 Provider | 已实现：本地 Qwen 默认、OpenAI 可选、隔离的 GPT-2 历史基线 |
| Web Demo | 已实现本地单进程版本：会话记忆、Agent Trace、引用、CSRF 与基础滥用控制 |
| 跨领域 Adapter | 规划中；健康 Prompt、安全策略、语料 Schema 和 UI 尚未抽离 |
| 生产级多用户服务 | 不支持；尚无认证授权、分布式限流、加密持久化、完整可观测性和合规控制 |

## 架构

```text
Governed Agent Lab
├── 平台核心
│   ├── 有界 Planner / Tool / Responder Runtime
│   ├── Provider 无关的预测与评测协议
│   ├── 受控来源校验与检索实验
│   └── 安全与隐私护栏
├── ClearCare Health 参考垂直场景
│   ├── 急症分流与澄清策略
│   ├── 项目编写的健康证据摘要
│   └── 本地网页演示与开发集测量
├── 开发者工作流
│   └── curate-health-evidence Codex Skill
└── 历史基线
    └── 原始 GPT-2 训练、推理代码与单独生成的数据
```

对于非急症请求，ClearCare Planner 只能选择一个白名单路径：请求必要补充、检索
受控证据，或不使用工具直接回答。强急症信号会在模型和限流之前进入固定提示。
Trace 只展示动作与结果数量，不暴露隐藏思维链。

## 用测量结果说话

以下结果来自小规模、项目内审核的**健康开发集**，只用于工程回归。它们不是独立
Benchmark，更不是临床性能结论。

| 指标 | Keyword 基线 | BM25 候选 |
|---|---:|---:|
| 本地 Qwen 任务成功代理指标 | 72.5% | 78.75% |
| Retrieval Recall@3 | 62.5% | 75.0% |
| 急症召回率 | 100% | 100% |
| 引用 ID 有效率 | 100% | 100% |

BM25 的选择与测量使用了同一个开发集，因此仍只是候选方案。晋级需要独立 Holdout
和回归门槛。详见 [Evaluation v1](docs/evaluation-v1.md)、
[RAG V2](docs/rag-v2-experiment.md) 与
[Evaluation MVP](docs/evaluation-mvp.md)。

## 快速开始

需要 Python 3.10+。确定性测试和评测不会下载模型，也不会产生 API 费用。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'

python scripts/validate_knowledge.py
pytest
python scripts/run_evaluation.py
```

### 启动本地 Qwen 网页

Apple Silicon 默认使用 MLX 量化 Qwen。首次运行会下载权重，需要足够内存。

```bash
python -m pip install -e '.[inference]'
export GOVERNED_AGENT_MODEL_PROVIDER="qwen-local"
export GOVERNED_AGENT_QWEN_MODEL="mlx-community/Qwen3-4B-Instruct-2507-4bit"
export GOVERNED_AGENT_QWEN_REVISION="50d427756c6b1b2fe0c0a10f67fbda1fc8e82c1b"
flask --app app run
```

访问 <http://127.0.0.1:5000>。追问时只输入新增信息，应用会自动提供有界的近期
上下文；点击“开始新咨询”即可清除当前会话。

### 可选 OpenAI 对照

OpenAI API 与 ChatGPT 订阅分开计费。默认云模型是官方文档中的
[`gpt-5.6-terra`](https://developers.openai.com/api/docs/models/gpt-5.6-terra)。
只有服务器开启且用户在当次请求明确选择时，才会使用云端。

```bash
python -m pip install -e '.[openai]'
export OPENAI_API_KEY="your_api_key"
export GOVERNED_AGENT_OPENAI_MODEL="gpt-5.6-terra"
export GOVERNED_AGENT_CLOUD_ENHANCEMENT_ENABLED=true
flask --app app run
```

请求设置了 `store=False`，但这不等于完整的零数据保留或合规保证。不要提交密钥，
也不要向云端发送敏感健康信息。

## 安全与部署边界

本地演示已加入 CSRF 防护、16 KiB 请求上限、单进程限流、安全 Cookie 默认值、
严格响应头、非持久化会话、证据来源绑定、输入/语料长度上限，以及不记录原始异常
内容。生产模式在缺少 32 位以上稳定密钥或安全 Cookie 时会拒绝启动。

```bash
export GOVERNED_AGENT_DEPLOYMENT_MODE=production
export GOVERNED_AGENT_SECRET_KEY="replace-with-a-random-secret-of-at-least-32-characters"
export GOVERNED_AGENT_SESSION_COOKIE_SECURE=true
```

这些控制**不会**让 Flask 开发服务器自动具备公网生产能力。系统没有用户认证授权、
分布式限流、加密持久会话、WAF、独立审计服务或医疗合规认证。如要公开部署，必须
先补齐这些边界。详见[安全与风险审计](docs/security-and-risk-review.md)和
[SECURITY.md](SECURITY.md)。

## 受控证据与数据来源

`knowledge/medical_guidance.json` 当前只有 3 条项目自行编写的中文摘要，链接到
CDC、NHS 和 WHO 页面，并明确标记为**未经临床人员审核**。它们不能被宣传为已
验证的临床建议。`knowledge/source_manifest.json` 定义获准机构、域名、复用状态、
地区和复核策略。运行时会拒绝未知或冒充来源、过期复核、未来日期、不安全 URL、
重复 ID、超长内容和哈希不一致记录。

简单增加文档不会自动提高可靠性。新增资料应该来自明确的覆盖缺口，并经过来源
治理、Holdout 评测和发布门槛。仓库中的
[`curate-health-evidence`](skills/curate-health-evidence/) Skill 可以自动执行确定性
校验，但不能替代临床审核。

## GPT-2 历史边界

原始 GPT-2 代码只保留为历史 CLI/训练基线，不再作为 Web Provider，也不参与默认
Runtime 和 Evaluation。仓库不再跟踪生成的 Pickle 与 Python 字节码；数据加载器
只接受有大小限制的整数 Token ID 列表并拒绝全局对象/类，模型只允许从本地
Safetensors 加载。

由于数据来源、去标识质量和再分发权都无法确认，当前工作树已经移除原始历史文本
与生成的 Pickle；Git 历史或上游快照仍可能保留早期内容。请在仓库外自行准备具有
合法来源且已去标识的数据，并显式生成本地产物：

```bash
python -m pip install -e '.[training]'
python data_preprocess/preprocess.py --input /path/to/train.txt --output local_data/train.pkl
python data_preprocess/preprocess.py --input /path/to/valid.txt --output local_data/valid.pkl
```

原始对话样本日志默认关闭。真实个人或健康信息场景不得开启。

## 仓库结构

```text
app.py, web_security.py          Web 编排与请求安全控制
agent_runtime.py                 有界规划、工具、回答 Runtime
chat_models.py                   Qwen 与 OpenAI Web Provider
conversation.py                 有界内存上下文
safety.py                        ClearCare 急症分流
knowledge.py, retrieval.py       受控语料校验与检索
evaluation/, scripts/            案例、捕获、报告与发布检查
skills/curate-health-evidence/   可安装的开发者 Codex Skill
docs/                            产品、评测、RAG、品牌与风险文档
data_preprocess/, train.py       隔离的 GPT-2 历史流程
tests/                           自动化回归与安全测试
```

## 产品与工程文档

- [Product Case Study](docs/product-case-study.md)
- [作品集升级路线图](docs/portfolio-upgrade-roadmap.md)
- [品牌架构](docs/brand-architecture.md)
- [Evaluation MVP](docs/evaluation-mvp.md) 与 [Evaluation v1](docs/evaluation-v1.md)
- [RAG V2 实验](docs/rag-v2-experiment.md)
- [安全与风险审计](docs/security-and-risk-review.md)

## 路线图

1. 冻结独立审核的 Holdout，并增加发布回归门槛。
2. 建立按场景、失败、延迟和成本切片的 Evaluation Dashboard。
3. 抽离版本化 Domain Adapter，覆盖策略、语料、指标和 UI。
4. 用第二个较低风险场景证明 Adapter 有效后，再宣称通用平台能力。
5. 只有在公网多用户产品成为明确目标后，才投入认证、持久隐私控制、可观测性和
   部署加固。

## 许可证与复用警告

上游项目没有声明开源许可证，历史训练数据的来源和复用权也没有解决。未经原作者
明确许可，不应假设代码或数据可以再分发或商用。本次技术清理不能消除该法律风险。
