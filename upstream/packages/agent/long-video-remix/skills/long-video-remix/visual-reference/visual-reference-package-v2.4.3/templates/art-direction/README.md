# Art Direction Tools

推荐入口：

```bash
python3 -I scripts/prepare_design_review.py <visual_dir>
```

默认生成 Art Direction brief、small-screen board 与机械 audit。只有确有 blur/squint 检查需求时加 `--blur`；只有实际独立盲审时加 `--blind` 生成 blind-map。

## 工具边界

1. `art_direction_brief.py`：把 V0/V1/V2 压成证据 brief，禁止生成器跳回空泛审美词。
2. `make_review_board.py`：从当前 V4 Mockup 默认生成 480px small-screen board；`--blur` 才生成 blur/squint；`--blind` 才随机化候选别名并生成绑定来源 Mockup SHA 的 blind-map。
3. `design_quality_audit.py`：只做机械审计，不自动宣称“高级感 PASS”；小屏字高只有项目显式配置绝对像素阈值时才判定。
4. `finalize_independent_review.py`：可选。把真正独立 reviewer 的响应绑定到当前 blind-map 与 board SHA。代码只能验证绑定，**不能证明 reviewer 真正独立**。
5. `make_motion_state_board.py`：动态方案做 before / enter / hold / exit 四态板。

## Gate 取舍

- small-screen board：**必需**；blur/squint board：按视觉问题使用，不需要时在 V5 记录理由。
- blind-map：只有真实独立盲审时才生成。独立盲审默认 **optional**；只有项目明确设置 `V0.design_review_policy.independent_review=required` 且确实有另一位 reviewer 时，才成为硬 Gate。
- 没有独立 reviewer 时，不允许同一个模型自评后伪装成“独立评审”；直接写 `independent_review.status=not_used`。
