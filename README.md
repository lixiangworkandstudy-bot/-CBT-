# 慢慢星 · MANMAN PLANET

**基于 CBT 原则的游戏化陪伴机器人：面向孤独症儿童社交沟通与情绪调节的辅助交互设计。**

选择机器人：维他动力 × 零零后科技大头机器狗（VBOT EDU）。当前交付为从零开发的本地交互 MVP、ROS 2 Humble / turtlesim 联动和待现场验收的 VBOT 板载适配器。**没有完成真机测试，也没有开展儿童研究或临床验证。**

## 立即运行

Windows：双击 `start-windows.cmd`；或在本目录运行：

```powershell
python -m app.server
```

浏览器打开 http://localhost:8787 。Python 3.10+ 即可，网页与业务服务均无第三方运行依赖，无 API Key。默认只监听本机回环地址。不打开摄像头或麦克风，不接云模型。关闭终端即停止服务，内存记录随进程退出清除。`start-windows.cmd` 依赖 `python` 已加入 PATH。

1. 点“一起开始”，由陪伴成人确认在场和活动说明。
2. 体验四个活动中的任意一个，每个活动 3 步，允许跳过、休息和非口语回应。
3. “我想休息”进入锁定的休息页；由成人明确确认后重新选择活动。
4. “共同回顾”查看、导出匿名选择记录；可清除本次记录。

网页中的慢慢为用户提供的绘本人物IP形象，**不是实拍或真机连接证明**。设备状态来自运行中的适配器心跳，单有心跳不证明物理动作执行成功。

## WSL2 + ROS 2 Humble 演示

建议服务与适配器同在 WSL 内运行，避开 Windows 与 WSL NAT 的 localhost 差异。Windows 演示服务与 WSL 演示服务选一套启动，不要同时争用 8787。

WSL 终端 A（先进入本项目文件夹）：

```bash
bash scripts/start-wsl.sh
```

Windows 浏览器打开 http://localhost:8787 ，进入活动后从 URL 复制 `session=` 后的 ID。

WSL 终端 B：

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=1
ros2 run turtlesim turtlesim_node
```

WSL 终端 C（本项目目录，替换 `SESSION_ID`）：

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=1
python3 -m robot.bridge --session SESSION_ID --mode turtlesim --execute --duration 120
```

完成一次活动后，海龟会收到短暂的原地缓慢转动提示，然后归零。适配器不会让海龟前进。仅运行 120 秒，超时后需要手动重启。若机器负载较高导致 0.6 秒提示窗口错过，可以重新完成一个活动；不要延长运动来掩盖延迟。

不加 `--execute` 时为 dry-run：不导入 ROS、不发布消息、不接触真机。服务器中断、指令过期或休息状态会令租约失效；适配器在独立于 HTTP 的 20Hz ROS 定时器上发布零速。

## 验证与证据

```bash
python3 -m unittest discover -s tests -v
source /opt/ros/humble/setup.bash
python3 scripts/check_environment.py
```

实际 turtlesim 自动集成测试（隔离 Domain 63，自动拉起并清理自己的服务、海龟、适配器；不连接真机）：

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=63 ROS_LOCALHOST_ONLY=1 QT_QPA_PLATFORM=offscreen
python3 scripts/verify_ros.py
```

浏览器 QA 可选用 Playwright：`npm install --no-save playwright` 后启动本地服务，再执行 `node scripts/verify_ui.cjs`；首次使用需要 `npx playwright install chromium`。这不是产品运行依赖。自动测试用模拟选择，不含真实儿童数据。

已保存：`evidence/wsl-environment.json`、`ros-integration.json`、`ui-tests.json`、`unit-tests.txt`、网页截图及 `demo.webm`。真实 ROS 测试结果见原始 JSON；测试环境不是机器人板载环境，不能用于勾选“真机 SDK 已配置”或“已获得开发权”。

## 项目文件

| 路径 | 用途 |
| --- | --- |
| `app/engine.py` | 四个规则驱动的活动、状态机、内存记录、动作短租约 |
| `app/server.py` | 回环地址 HTTP 服务，静态页面与 API |
| `app/web/` | 响应式儿童活动页与成人空间 |
| `robot/bridge.py` | dry-run / turtlesim / 受闸门约束的 VBOT ROS 适配器 |
| `tests/` | 关键状态转移与动作边界验证 |
| `docs/产品设计.md` | 用户、CBT 映射、活动设计、评估计划 |
| `docs/真机部署.md` | 板载通信路径、环境、分阶段验收与回退 |
| `docs/提交表格3-11.md` | 可复制的提交文案与真实状态 |
| `docs/演示脚本.md` | 3 分钟演示及截图上传建议 |
| `docs/路演海报.html` | 可编辑海报源文件 |
| `evidence/路演海报.png` | 可上传海报 |

## 当前边界

规则驱动 Agent 已实现，不是开放式聊天机器人。无需大模型就能展示“输入—状态判断—引导—可选设备提示—回顾”的完整闭环。语音、触摸、头部动作、板载灯光及 RCP 编排属于下一阶段，不在本版中冒充完成。孩子的主观感受来自其自主选择，不由表情、声音或动作推断。

本地版本面向单个家庭/工位的演示，不作为公网多用户系统或临床产品部署。session ID 是临时能力标识，拥有 ID 的本地进程可访问记录；导出文件需要成人自行保管。服务内最多保留 100 次会话，超出后淘汰最旧会话。真机功能需先核对设备版本、现场权限和桥接话题，详见部署文档。

## 资料与许可

依据根目录《2026 选手参与手册.docx》及用户提供的表格截图设计。手册作为资料读取，不将其中面向参赛者的操作要求自动执行成对外提交或消息。

技术来源：[VBOT 教程](https://zhangzhenyao.com/vbot-docs/)；[官方 vbot-lab](https://github.com/VitaDynamics/vbot-lab)，核对的快照 SHA：`26bd51d9397a46ed3cc008abeb46c8b9f36f3279`。技术摘录保存在 `docs/sources/` 供核对，版权属于原作者；请以设备实际交付与官方当前文档为准。源文档存在话题映射差异时优先官方仓库和现场发现结果。

项目原创代码见 `LICENSE`（MIT）；用户提供的IP图像与其衍生素材、第三方资料、品牌名称和文档不在本项目 MIT 授权范围内。
