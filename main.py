from typing import Optional

from inspur.config_manager import ConfigManager
from inspur.inspur_client import InspurClient
from inspur.user_manager import UserManager
from utils.common_utils import get_numeric_choice
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


class InspurSystem:
    def __init__(self) -> None:
        self.config_manager = ConfigManager()
        self.user_manager = UserManager(self.config_manager)
        self.inspur: Optional[InspurClient] = None

    def _validate_inspur_client(self) -> bool:
        if not self.inspur:
            logger.error("客户端未初始化")
            return False
        return True

    def _get_attendance_site_if_needed(self) -> bool:
        if self.inspur.ensure_attendance_site_loaded():
            return True

        attendance_result = self.inspur.get_attendance_sites()

        if "error" in attendance_result:
            logger.error("获取考勤点失败: {}", attendance_result.get("error"))
            logger.info("请重新选择操作")
            return False

        if attendance_result["attendanceSites"]:
            sites = attendance_result["attendanceSites"]
            selected_site_data = self.inspur._select_attendance_site(sites, "考勤")

            if selected_site_data:
                selected_site = {
                    "id": str(selected_site_data["id"]),
                    "latitude": selected_site_data["latitude"],
                    "longitude": selected_site_data["longitude"],
                    "address": selected_site_data["address"],
                }
                self.inspur.attendance_site = selected_site

                config_manager = ConfigManager()
                attendance_sites = {
                    site["address"]: {
                        "id": str(site["id"]),
                        "latitude": site["latitude"],
                        "longitude": site["longitude"],
                    }
                    for site in sites
                }
                site_address = selected_site["address"]
                config_manager.save_attendance_sites(attendance_sites)
                config_manager.save_checkin_site(site_address)

                logger.info("✓ 已选择考勤点: {}", selected_site["address"])
                return True
            else:
                logger.warning("未选择考勤点，操作取消")
                logger.info("请重新选择操作")
                return False
        else:
            logger.error("未找到考勤点")
            logger.info("请重新选择操作")
            return False

    def process_attendance_query(
        self, inspur: InspurClient, config: dict, action_type: str = ""
    ) -> None:
        if config["auto_query_after_check"]:
            # 自动查询考勤记录
            inspur.get_monthly_attendance(last_only=True, action_type=action_type)
        else:
            query_choice = input("是否需要查询考勤记录？(y/n): ").strip().lower()
            if query_choice == "y":
                inspur.get_monthly_attendance(last_only=True, action_type=action_type)

    def re_select_attendance_site(self) -> None:
        if not self._validate_inspur_client():
            return

        self.inspur.attendance_site = {}
        attendance_result = self.inspur.get_attendance_sites()

        if "error" in attendance_result:
            logger.warning("获取考勤点失败")
            return

        if not attendance_result["attendanceSites"]:
            logger.warning("未找到考勤点")
            return

        sites = attendance_result["attendanceSites"]
        selected_site_data = self.inspur._select_attendance_site(sites, "")

        if not selected_site_data:
            logger.warning("未选择考勤点")
            return

        selected_site = {
            "id": str(selected_site_data["id"]),
            "latitude": selected_site_data["latitude"],
            "longitude": selected_site_data["longitude"],
            "address": selected_site_data["address"],
        }
        self.inspur.attendance_site = selected_site

        config_manager = ConfigManager()
        attendance_sites = {
            site["address"]: {
                "id": str(site["id"]),
                "latitude": site["latitude"],
                "longitude": site["longitude"],
            }
            for site in sites
        }
        site_address = selected_site["address"]
        config_manager.save_attendance_sites(attendance_sites)
        config_manager.save_checkin_site(site_address)

        logger.info(
            "已重新选择考勤点: {}",
            self.inspur.attendance_site["address"],
        )

    def _display_main_menu(self) -> None:
        logger.info("请选择操作：")
        logger.info("1. 签到")
        logger.info("2. 签退")
        logger.info("3. 查询考勤记录")
        logger.info("4. 切换用户")
        logger.info("5. 重新选择考勤点")
        logger.info("6. 退出程序")
        logger.info("")

    def _handle_attendance_action(self, choice: str, config: dict) -> None:
        if not self._validate_inspur_client():
            return

        action_name = "签到" if choice == "1" else "签退"
        check_method = self.inspur.check_in if choice == "1" else self.inspur.check_out

        logger.info("")
        check_result = check_method()

        if check_result and check_result.get("success"):
            self.process_attendance_query(self.inspur, config, action_name)
        else:
            logger.warning("签到/签退操作未完成")

    def _handle_query_action(self) -> None:
        if not self._validate_inspur_client():
            return

        logger.info("请选择查询类型：")
        logger.info("a) 查询当前月考勤记录")
        logger.info("b) 查询指定月份考勤记录")
        logger.info("c) 返回主菜单")
        logger.info("")

        query_type = input("请选择 (a/b/c): ").strip().lower()
        logger.info("")

        if query_type == "a":
            self.inspur.get_monthly_attendance(last_only=False)
        elif query_type == "b":
            month_input = input("请输入月份 (格式: YYYY-MM，如 2025-01): ").strip()
            try:
                # 验证输入格式
                parts = month_input.split("-")
                if len(parts) == 2 and len(parts[0]) == 4 and len(parts[1]) == 2:
                    year, month = parts
                    if year.isdigit() and month.isdigit():
                        self.inspur.get_monthly_attendance(month=month_input)
                        return
                logger.warning("月份格式不正确")
            except Exception as e:
                logger.error("查询失败: {}", e)
        elif query_type == "c":
            return
        else:
            logger.warning("无效选择")

    def run(self) -> None:
        config = self.config_manager.load_config()
        setup_logging(config["log_level"])

        logger.info("=== 移动考勤 ===")

        try:
            self.inspur = InspurClient(
                base_url=config["base_url"],
                random_radius_meters=config["random_radius_meters"],
            )
            logger.info("")

            while True:
                credentials = self.user_manager.get_user_credentials()
                if not credentials:
                    logger.error("获取用户凭据失败，程序退出")
                    return

                phone, password, used_saved_password, logged_in_inspur = credentials
                if not phone or not password:
                    logger.error("获取用户凭据失败，程序退出")
                    return

                if logged_in_inspur:
                    self.inspur = logged_in_inspur
                    break
                else:
                    logger.error("登录失败，请重新输入凭据")
                    continue

            logger.info("")

            try:
                while True:
                    self._display_main_menu()

                    choice = get_numeric_choice("请输入选择 (1-6): ", 1, 6, 3)

                    if choice is None:
                        logger.warning("无效选择，请输入 1-6")
                        continue

                    choice_str = str(choice)
                    logger.info("")

                    if choice_str in ["1", "2"]:
                        self._handle_attendance_action(choice_str, config)

                    elif choice_str == "3":
                        self._handle_query_action()

                    elif choice_str == "4":
                        result = self.user_manager.switch_user()
                        if result:
                            phone, password, used_saved_password, logged_in_inspur = (
                                result
                            )
                            self.inspur = logged_in_inspur

                    elif choice_str == "5":
                        self.re_select_attendance_site()
                        continue

                    elif choice_str == "6":
                        logger.info("感谢使用，程序退出！")
                        break

                    logger.info("")
                    logger.info("-" * 50)
                    logger.info("")

            except KeyboardInterrupt:
                logger.warning("程序被用户中断")
            except Exception as e:
                logger.error("程序执行出错: {}", e)
                logger.exception("异常堆栈")
            finally:
                if self.inspur:
                    self.inspur.close()
                    logger.info("会话已关闭")

        except Exception as e:
            logger.error("系统初始化失败: {}", e)
            logger.exception("异常堆栈")


def main() -> None:
    try:
        system = InspurSystem()
        system.run()
    except KeyboardInterrupt:
        logger.warning("程序被用户中断")
    except Exception as e:
        logger.error("程序启动失败: {}", e)
        logger.exception("异常堆栈")


if __name__ == "__main__":
    main()
