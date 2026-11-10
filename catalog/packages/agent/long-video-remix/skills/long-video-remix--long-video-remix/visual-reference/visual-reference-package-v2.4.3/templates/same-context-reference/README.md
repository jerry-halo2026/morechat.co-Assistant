# Same-context reference capture template

用于把 XR/MR 从“原则可用”提升为真正 `measured` 的同条件参考。第三方画面只保留在本地 capture 目录，不随包分发；包内只记录 locator、SHA 和测量结果。

每个静态帧必须至少标 `text + subject + relationship_note + why_it_works`。动态 MR 另外填写 `timing.json`。运行：

```bash
python3 -I scripts/measure_batch.py capture/ --package .
```

目标不是积累截图数量，而是让参考能回答：文字离人物/动作多远、如何避让、出现/停留/退出时机，以及为什么这个处理在该镜头成立。
