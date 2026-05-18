# 产品中心测试用例

## 1. 测试范围

本测试用例基于当前产品中心需求与自动化脚本配置生成，覆盖 App 内产品中心入口、国家/地区切换、购买渠道展示与跳转、主打产品展示与跳转、外部 App/浏览器恢复等场景。

当前配置范围：

| 类型 | 范围 |
| --- | --- |
| 国家/地区 | 中国、美国、加拿大、墨西哥、英国、德国、法国、日本、其他地区 |
| 中国渠道 | 淘宝、JD |
| 海外渠道 | Amazon、AliExpress、本地经销商 |
| 其他地区渠道 | 本地经销商 |
| 主打产品 | CoMo SE、大师4K II、S60 滑轨、大师4K Lite、SE 4K、大师 4K、M7系列、CoMo |
| 被测 App | `com.accsoon.uvctransmission` |

## 2. 前置条件

| 编号 | 前置条件 |
| --- | --- |
| PRE-001 | Android 设备已连接，ADB 状态为 `device`。 |
| PRE-002 | 被测 App 已安装并可正常启动。 |
| PRE-003 | Appium 服务可用，默认地址为 `http://127.0.0.1:4725/wd/hub`。 |
| PRE-004 | 设备网络可访问淘宝、京东、Amazon、AliExpress、accsoon 官网等外部页面。 |
| PRE-005 | 若设备已安装购物 App，允许从被测 App 跳转；未安装时允许拉起浏览器网页。 |
| PRE-006 | 测试前关闭影响操作的系统弹窗，或在用例中验证广告弹窗关闭逻辑。 |

## 3. 冒烟测试

| 用例编号 | 用例名称 | 操作步骤 | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| PC-SMOKE-001 | Appium 连接冒烟 | 1. 启动 Appium。<br>2. 连接 Android 设备。<br>3. 创建 Appium session。 | session 创建成功，被测 App 能启动到首页或启动页。 | P0 |
| PC-SMOKE-002 | 进入产品中心 | 1. 启动被测 App。<br>2. 如出现广告弹窗，点击关闭。<br>3. 点击菜单按钮进入产品中心。 | 成功进入产品中心，页面可见 `产品中心` 或 `Accsoon News`、主打产品、购买渠道区域。 | P0 |

## 4. 产品中心入口与页面展示

| 用例编号 | 用例名称 | 操作步骤 | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| PC-HOME-001 | 广告弹窗关闭后进入产品中心 | 1. 启动 App。<br>2. 触发或等待广告弹窗。<br>3. 点击关闭按钮。<br>4. 点击菜单按钮。 | 弹窗关闭成功，点击菜单后进入产品中心。 | P0 |
| PC-HOME-002 | 无广告弹窗时进入产品中心 | 1. 启动 App。<br>2. 确认当前无广告弹窗。<br>3. 点击菜单按钮。 | 不依赖弹窗关闭动作，仍可进入产品中心。 | P0 |
| PC-HOME-003 | 产品中心基础元素展示 | 1. 进入产品中心。<br>2. 检查页面关键元素。 | 页面显示 `产品中心` 或 `Accsoon News`，至少显示一个主打产品，购买渠道区域可见。 | P0 |
| PC-HOME-004 | 默认国家为中国 | 1. 进入产品中心。<br>2. 查看购买渠道国家选择器。 | 默认选中或可切换到中国；中国状态下展示淘宝、JD。 | P1 |

## 5. 国家/地区下拉选择

| 用例编号 | 用例名称 | 操作步骤 | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| PC-COUNTRY-001 | 展开国家/地区下拉 | 1. 进入产品中心。<br>2. 点击国家/地区选择器。 | 国家/地区下拉列表展开。 | P0 |
| PC-COUNTRY-002 | 国家/地区选项完整性 | 1. 展开国家/地区下拉。<br>2. 检查全部选项。 | 列表包含中国、美国、加拿大、墨西哥、英国、德国、法国、日本、其他地区。 | P0 |
| PC-COUNTRY-003 | 切换国家后选中态更新 | 1. 展开国家/地区下拉。<br>2. 选择任一国家。<br>3. 查看选择器展示。 | 选择器展示为新选择的国家，购买渠道同步刷新。 | P0 |
| PC-COUNTRY-004 | 连续切换多个国家 | 1. 依次选择中国、美国、日本、其他地区。<br>2. 每次切换后检查页面。 | 每次切换后页面无崩溃，国家选中态和渠道展示正确。 | P1 |

## 6. 购买渠道展示

| 用例编号 | 国家/地区 | 预期渠道 | 操作步骤 | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| PC-CHANNEL-001 | 中国 | 淘宝、JD | 1. 选择中国。<br>2. 查看购买渠道。 | 展示淘宝、JD。 | P0 |
| PC-CHANNEL-002 | 美国 | Amazon、AliExpress、本地经销商 | 1. 选择美国。<br>2. 查看购买渠道。 | 展示 Amazon、AliExpress、本地经销商。 | P0 |
| PC-CHANNEL-003 | 加拿大 | Amazon、AliExpress、本地经销商 | 1. 选择加拿大。<br>2. 查看购买渠道。 | 展示 Amazon、AliExpress、本地经销商。 | P0 |
| PC-CHANNEL-004 | 墨西哥 | Amazon、AliExpress、本地经销商 | 1. 选择墨西哥。<br>2. 查看购买渠道。 | 展示 Amazon、AliExpress、本地经销商。 | P0 |
| PC-CHANNEL-005 | 英国 | Amazon、AliExpress、本地经销商 | 1. 选择英国。<br>2. 查看购买渠道。 | 展示 Amazon、AliExpress、本地经销商。 | P0 |
| PC-CHANNEL-006 | 德国 | Amazon、AliExpress、本地经销商 | 1. 选择德国。<br>2. 查看购买渠道。 | 展示 Amazon、AliExpress、本地经销商。 | P0 |
| PC-CHANNEL-007 | 法国 | Amazon、AliExpress、本地经销商 | 1. 选择法国。<br>2. 查看购买渠道。 | 展示 Amazon、AliExpress、本地经销商。 | P0 |
| PC-CHANNEL-008 | 日本 | Amazon、AliExpress、本地经销商 | 1. 选择日本。<br>2. 查看购买渠道。 | 展示 Amazon、AliExpress、本地经销商。 | P0 |
| PC-CHANNEL-009 | 其他地区 | 本地经销商 | 1. 选择其他地区。<br>2. 查看购买渠道。 | 展示本地经销商。 | P0 |

## 7. 购买渠道跳转

| 用例编号 | 国家/地区 | 渠道 | 操作步骤 | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| PC-JUMP-001 | 中国 | 淘宝 | 1. 选择中国。<br>2. 点击淘宝。 | 跳转到淘宝 App 或淘宝网页，页面 URL/标识包含 `taobao` 或淘宝相关信息。 | P0 |
| PC-JUMP-002 | 中国 | JD | 1. 选择中国。<br>2. 点击 JD。 | 跳转到京东 App 或京东网页，页面 URL/标识包含 `jd.com`、`jingdong` 或京东相关信息。 | P0 |
| PC-JUMP-003 | 美国 | Amazon | 1. 选择美国。<br>2. 点击 Amazon。 | 跳转到 Amazon 美国页面，URL/页面标识包含 `amazon.com`。 | P0 |
| PC-JUMP-004 | 美国 | AliExpress | 1. 选择美国。<br>2. 点击 AliExpress。 | 跳转到 AliExpress App 或网页，URL/页面标识包含 `aliexpress`。 | P0 |
| PC-JUMP-005 | 美国 | 本地经销商 | 1. 选择美国。<br>2. 点击本地经销商。 | 跳转到 Accsoon 官网或经销商网页，URL/页面标识包含 `accsoon.com`。 | P0 |
| PC-JUMP-006 | 加拿大 | Amazon | 1. 选择加拿大。<br>2. 点击 Amazon。 | 跳转到 Amazon 加拿大页面，URL/页面标识包含 `amazon.ca`。 | P0 |
| PC-JUMP-007 | 加拿大 | AliExpress | 1. 选择加拿大。<br>2. 点击 AliExpress。 | 跳转到 AliExpress App 或网页，URL/页面标识包含 `aliexpress`。 | P0 |
| PC-JUMP-008 | 加拿大 | 本地经销商 | 1. 选择加拿大。<br>2. 点击本地经销商。 | 跳转到 Accsoon 官网或经销商网页，URL/页面标识包含 `accsoon.com`。 | P0 |
| PC-JUMP-009 | 墨西哥 | Amazon | 1. 选择墨西哥。<br>2. 点击 Amazon。 | 跳转到 Amazon 墨西哥页面，URL/页面标识包含 `amazon.com.mx`。 | P0 |
| PC-JUMP-010 | 墨西哥 | AliExpress | 1. 选择墨西哥。<br>2. 点击 AliExpress。 | 跳转到 AliExpress App 或网页，URL/页面标识包含 `aliexpress`。 | P0 |
| PC-JUMP-011 | 墨西哥 | 本地经销商 | 1. 选择墨西哥。<br>2. 点击本地经销商。 | 跳转到 Accsoon 官网或经销商网页，URL/页面标识包含 `accsoon.com`。 | P0 |
| PC-JUMP-012 | 英国 | Amazon | 1. 选择英国。<br>2. 点击 Amazon。 | 跳转到 Amazon 英国页面，URL/页面标识包含 `amazon.co.uk`。 | P0 |
| PC-JUMP-013 | 英国 | AliExpress | 1. 选择英国。<br>2. 点击 AliExpress。 | 跳转到 AliExpress App 或网页，URL/页面标识包含 `aliexpress`。 | P0 |
| PC-JUMP-014 | 英国 | 本地经销商 | 1. 选择英国。<br>2. 点击本地经销商。 | 跳转到 Accsoon 官网或经销商网页，URL/页面标识包含 `accsoon.com`。 | P0 |
| PC-JUMP-015 | 德国 | Amazon | 1. 选择德国。<br>2. 点击 Amazon。 | 跳转到 Amazon 德国页面，URL/页面标识包含 `amazon.de`。 | P0 |
| PC-JUMP-016 | 德国 | AliExpress | 1. 选择德国。<br>2. 点击 AliExpress。 | 跳转到 AliExpress App 或网页，URL/页面标识包含 `aliexpress`。 | P0 |
| PC-JUMP-017 | 德国 | 本地经销商 | 1. 选择德国。<br>2. 点击本地经销商。 | 跳转到 Accsoon 官网或经销商网页，URL/页面标识包含 `accsoon.com`。 | P0 |
| PC-JUMP-018 | 法国 | Amazon | 1. 选择法国。<br>2. 点击 Amazon。 | 跳转到 Amazon 法国页面，URL/页面标识包含 `amazon.fr`。 | P0 |
| PC-JUMP-019 | 法国 | AliExpress | 1. 选择法国。<br>2. 点击 AliExpress。 | 跳转到 AliExpress App 或网页，URL/页面标识包含 `aliexpress`。 | P0 |
| PC-JUMP-020 | 法国 | 本地经销商 | 1. 选择法国。<br>2. 点击本地经销商。 | 跳转到 Accsoon 官网或经销商网页，URL/页面标识包含 `accsoon.com`。 | P0 |
| PC-JUMP-021 | 日本 | Amazon | 1. 选择日本。<br>2. 点击 Amazon。 | 跳转到 Amazon 日本页面，URL/页面标识包含 `amazon.co.jp`。 | P0 |
| PC-JUMP-022 | 日本 | AliExpress | 1. 选择日本。<br>2. 点击 AliExpress。 | 跳转到 AliExpress App 或网页，URL/页面标识包含 `aliexpress`。 | P0 |
| PC-JUMP-023 | 日本 | 本地经销商 | 1. 选择日本。<br>2. 点击本地经销商。 | 跳转到 Accsoon 官网或经销商网页，URL/页面标识包含 `accsoon.com`。 | P0 |
| PC-JUMP-024 | 其他地区 | 本地经销商 | 1. 选择其他地区。<br>2. 点击本地经销商。 | 跳转到 Accsoon 官网或经销商网页，URL/页面标识包含 `accsoon.com`。 | P0 |
| PC-JUMP-025 | 其他地区 | 主打产品官网 | 1. 选择其他地区。<br>2. 依次点击已配置 `global_officialproducturl` 的主打产品。 | 跳转到对应 Accsoon 官网产品页，URL/页面标识命中后台配置的 `global_officialproducturl`。 | P0 |

## 8. 主打产品展示与跳转

| 用例编号 | 用例名称 | 操作步骤 | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| PC-PRODUCT-001 | 主打产品列表展示 | 1. 进入产品中心。<br>2. 查看主打产品区域。 | 展示 CoMo SE、大师4K II、S60 滑轨、大师4K Lite、SE 4K、大师 4K、M7系列、CoMo。 | P0 |
| PC-PRODUCT-002 | CoMo SE 跳转 | 1. 依次选择各国家/地区。<br>2. 点击 CoMo SE。 | 跳转到该国家/地区对应的购买页或产品页，页面标识符合配置。 | P0 |
| PC-PRODUCT-003 | S60 滑轨跳转 | 1. 依次选择各国家/地区。<br>2. 点击 S60 滑轨。 | 跳转到该国家/地区对应的购买页或产品页，页面标识符合配置。 | P0 |
| PC-PRODUCT-004 | 大师4K Lite 跳转 | 1. 依次选择各国家/地区。<br>2. 点击大师4K Lite。 | 跳转到该国家/地区对应的购买页或产品页，页面标识符合配置。 | P0 |
| PC-PRODUCT-005 | SE 4K 跳转 | 1. 依次选择各国家/地区。<br>2. 点击 SE 4K。 | 跳转到该国家/地区对应的购买页或产品页，页面标识符合配置。 | P0 |
| PC-PRODUCT-006 | 大师 4K 跳转 | 1. 依次选择各国家/地区。<br>2. 点击大师 4K。 | 跳转到该国家/地区对应的购买页或产品页，页面标识符合配置。 | P0 |
| PC-PRODUCT-007 | M7系列跳转 | 1. 依次选择各国家/地区。<br>2. 点击 M7系列。 | 跳转到该国家/地区对应的购买页或产品页，页面标识符合配置。 | P0 |
| PC-PRODUCT-008 | CoMo 跳转 | 1. 依次选择各国家/地区。<br>2. 点击 CoMo。 | 跳转到该国家/地区对应的购买页或产品页，页面标识符合配置。 | P0 |
| PC-PRODUCT-009 | 大师4K II 链接配置确认 | 1. 依次选择各国家/地区。<br>2. 查看大师4K II 是否展示。<br>3. 如可点击，点击大师4K II。 | 当前配置中该产品链接为 `null`，需确认需求：若应跳转，则补齐链接；若不应跳转，则点击后不应出现错误跳转或崩溃。 | P1 |

主打产品跳转配置当前覆盖 63 个组合：9 个国家/地区乘以 7 个已配置链接产品。其他地区使用 `global_officialproducturl` 校验 Accsoon 官网产品页。`SeeMo 4K`、`SeeMo 4k`、`大师4K II` 的 9 个国家/地区组合暂未形成可验证跳转配置。

## 9. 跳转后恢复

| 用例编号 | 用例名称 | 操作步骤 | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| PC-RECOVER-001 | 从浏览器返回产品中心 | 1. 点击任一会打开浏览器的渠道或产品。<br>2. 等待外部网页打开。<br>3. 点击系统返回键。 | 能回到被测 App 产品中心，原国家/地区状态尽量保持。 | P0 |
| PC-RECOVER-002 | 从购物 App 返回产品中心 | 1. 点击任一会打开购物 App 的渠道或产品。<br>2. 等待外部 App 打开。<br>3. 点击系统返回键或切回被测 App。 | 能回到被测 App 产品中心，可继续执行下一条跳转验证。 | P0 |
| PC-RECOVER-003 | 外部页面无法返回时恢复 | 1. 点击任一渠道或产品跳转外部页面。<br>2. 模拟返回失败或页面停留。<br>3. 重新激活被测 App。 | 被测 App 可恢复到产品中心或重新进入产品中心，不影响后续用例。 | P1 |
| PC-RECOVER-004 | 硬重置恢复 | 1. 设置 `HARD_RESET_AFTER_JUMP=1`。<br>2. 执行任一跳转用例。<br>3. 验证跳转后恢复。 | 通过重启被测 App 的方式恢复，后续用例可继续执行。 | P2 |

## 10. 异常与兼容场景

| 用例编号 | 用例名称 | 操作步骤 | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| PC-EXCEPTION-001 | 网络不可用时点击购买渠道 | 1. 断开设备网络。<br>2. 进入产品中心。<br>3. 点击任一购买渠道。 | App 不崩溃；可出现系统网络错误、浏览器错误页或应用内可理解的失败状态。 | P1 |
| PC-EXCEPTION-002 | 未安装购物 App 时跳转 | 1. 卸载或禁用目标购物 App。<br>2. 点击对应渠道。 | 可通过浏览器打开对应网页，或给出明确可处理的跳转失败状态；App 不崩溃。 | P1 |
| PC-EXCEPTION-003 | 已安装购物 App 时跳转 | 1. 安装目标购物 App。<br>2. 点击对应渠道。 | 可拉起目标购物 App，或在系统选择器中出现目标 App。 | P1 |
| PC-EXCEPTION-004 | 快速连续点击渠道 | 1. 选择任一国家。<br>2. 快速多次点击同一渠道。 | 不出现重复打开导致的崩溃、卡死或无法返回。 | P2 |
| PC-EXCEPTION-005 | 国家切换后立即点击渠道 | 1. 切换国家。<br>2. 页面刚刷新后立即点击渠道。 | 渠道和目标国家一致，不跳转到上一个国家的链接。 | P1 |
| PC-EXCEPTION-006 | 横竖屏或分辨率兼容 | 1. 在不同分辨率设备上进入产品中心。<br>2. 检查主打产品、国家选择器、购买渠道。 | 关键元素可见且可点击，无明显遮挡。 | P2 |

## 11. 自动化用例映射

| 自动化测试 | 覆盖内容 |
| --- | --- |
| `test_01_enter_product_center` | 进入产品中心、基础元素展示、默认国家检查。 |
| `test_02_country_dropdown_options` | 国家/地区下拉选项完整性。 |
| `test_02_country_switch_updates_purchase_channels` | 连续切换中国、美国、日本、其他地区后，验证国家选中态和购买渠道同步刷新。 |
| `test_02_purchase_channels_display` | 各国家/地区购买渠道展示完整性，覆盖中国、海外国家和其他地区。 |
| `test_03_purchase_channels_jump` | 8 个国家的购买渠道展示与跳转，共 23 个渠道组合。 |
| `test_04_featured_products_display` | 主打产品列表展示完整性。 |
| `test_04_featured_products_jump` | 主打产品在各国家/地区下的展示与跳转。 |
| `test_05_other_region_direct_jump` | 其他地区本地经销商跳转官网，并校验主打产品跳转到对应官网产品页。 |
| `tests/test_product_center_config.py` | 本地配置级回归：国家/渠道矩阵、店铺链接、主打产品链接和 URL 标识解析。 |

## 12. 验收标准

| 编号 | 验收标准 |
| --- | --- |
| AC-001 | 产品中心可稳定进入，页面关键元素可见。 |
| AC-002 | 国家/地区下拉选项完整，选中后页面状态和渠道正确刷新。 |
| AC-003 | 中国展示淘宝、JD，美国到日本展示 Amazon、AliExpress、本地经销商，其他地区展示本地经销商。 |
| AC-004 | 点击渠道后能跳转到对应购物 App 或网页，目标域名/页面标识正确。 |
| AC-005 | 点击已配置链接的主打产品后能跳转到对应购买页或产品页。 |
| AC-006 | 每次外部跳转后能恢复到被测 App，并可继续执行后续用例。 |
| AC-007 | 网络异常、未安装购物 App、快速点击等场景下 App 不崩溃。 |
| AC-008 | `大师4K II` 的跳转需求需明确：补齐链接后纳入 P0 跳转验证，或明确为仅展示不跳转。 |
