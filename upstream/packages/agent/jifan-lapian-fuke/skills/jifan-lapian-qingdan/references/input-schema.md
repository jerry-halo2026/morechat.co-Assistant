# 输入结构

## 输入结构

顶层字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| topic | string | 是 | 这份成稿的主题，会成为标题 |
| items | array | 是 | 至少 1 项，结构见下 |
| pending | array | 否 | 你自己标注的待确认事项，会原样列进成稿 |

`items[]`（计划步骤）：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| step | string | 否 | 顺序号，缺省按数组序 |
| when | string | 否 | 时间或阶段 |
| what | string | 是 | 具体动作 |
| owner | string | 否 | 谁来做 |
| note | string | 否 | 备注 |
