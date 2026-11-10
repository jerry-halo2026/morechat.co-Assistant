# Motion Implementation Map v2.0 — Visual Reference Library 2.0

## 三条证据链必须分开

1. **Screen / Observed Reference**：第三方 REF 实际可见的构图、材质、层级、空间或运动线索；
2. **Source Implementation Evidence**：只有公开工程/作者资料真正支持时，才记录原作实现信息；
3. **Our Implementation Method**：IR-01–IR-11 是我们的 Blender / FFmpeg 实现路线，不能反写成原作技术栈。

## 11 套 Implementation Rig / System

### IR-01 · Transform Timing Rig
- 覆盖：`T01, T02, T03, T04, T05, T06, T07`
- 实现基座：F-Curves + Drivers + custom properties; optional offset tooling
- 主要控制：`progress, delay_frames, stiffness, damping, overshoot, hold_frames, phase, seed`

### IR-02 · Camera Depth Rig
- 覆盖：`C01, C02, C03, C04, C05, C06, C07, C08`
- 实现基座：Camera + Follow Path + Damped/Locked Track + depth planes + DOF
- 主要控制：`camera_path, offset_factor, look_target, lens, focus_target, fstop, depth_spacing, drift`

### IR-03 · Tracking & Occlusion Rig
- 覆盖：`S01, S02, S03, S04, S05`
- 实现基座：Movie Clip tracking + Camera/Object Solver + Follow Track + depth geometry/mattes
- 主要控制：`clip, track_name, use_3d_position, surface_proxy, occluder, handoff_influence`

### IR-04 · Spatial Typography Rig
- 覆盖：`G01, G02, G03, G04, G06, G07`
- 实现基座：Text/planes + Grease Pencil + Build + masks + stagger controls
- 主要控制：`char_delay, build_factor, mask_progress, world_anchor, divider, annotation_hold`

### IR-05 · Morph & Deform Rig
- 覆盖：`G05, R07, D01, D02`
- 实现基座：Shape Keys + Lattice/Displace + Geometry Nodes
- 主要控制：`shape_value, evaluation_time, deform_strength, falloff`

### IR-06 · Transition Choreography Rig
- 覆盖：`R01, R02, R03, R04, R05, R06`
- 实现基座：Geometry occlusion + camera path + DOF + light/compositor; editorial match when appropriate
- 主要控制：`transition_window, occluder_path, match_vector, camera_path, focus_curve, light_curve`

### IR-07 · Material & Optical Rig
- 覆盖：`I01, I02, I03, I04, I05, I06, I07`
- 实现基座：Principled materials + lights + render motion blur + compositor
- 主要控制：`roughness, ior, transmission, light_energy, shutter, grain, distortion, glow`

### IR-08 · Simulation Rig
- 覆盖：`D03, D04, D05, D06, D07, D08, P03`
- 实现基座：Soft/Rigid/Cloth + Geometry Nodes Simulation Zone + particles/volumes
- 主要控制：`mass, damping, collision, timestep, seed, cache, bake`

### IR-09 · Procedural Response Rig
- 覆盖：`P01, P02, P04, P06`
- 实现基座：Geometry Proximity + fields + Random Value + Sample Sound Frequencies + drivers
- 主要控制：`distance, falloff, seed, frequency_band, smoothing, response_range`

### IR-10 · Modular Motion System
- 覆盖：`P05, T04, T05, T06, G06`
- 实现基座：Collections + custom-property master controls + drivers/actions/NLA + component offsets
- 主要控制：`state, progress, component_delay, component_scale, motion_role, override`

### IR-11 · Editorial Time Rig
- 覆盖：`T08, T09, E01, E02, E03, E04, E05`
- 实现基座：VSE/compositor/planes when spatial; otherwise prefer FFmpeg timeline
- 主要控制：`source_range, speed_curve, crop_rect, freeze_hold, replay_count, time_offset, split_state`

## 当前项目使用规则

- Router 仍然先看当前真实 Keyframe 和视觉问题，用当前项目素材核对机制是否需要；
- 如果需要动态/空间机制，再从 Motion ID 路由到 IR；
- IR 规格用于选定实现方式，最终效果在当前项目 Mockup 和 Proof 中验证；
- 进入当前项目 Implementation Lock 时，将实现元素和可解析参数路径写入当前工程。
## IR-12 · Caption Slot & Adaptive Protection

- 覆盖：`L01 槽位选择, L02 自适应保护, L03 明暗切换, L04 锚点吸附`（v2.1 新增的屏幕文字落位 ID）
- 实现基座：Pillow + numpy 静帧工具；cue sheet 驱动；字体 / 颜色 / 字号由项目方案传入，工具不带内置风格
- 主要控制：`slot, slots_allowed, anchor, protection_cap, floor_exempt, style`
- 可选工具：`scripts/caption_place.py`，输入当前项目的 cue sheet 与帧图。
- Blender / FFmpeg 复刻：按同参数实现并单独 Proof；本版未验证像素一致性
