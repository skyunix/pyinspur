import hashlib
from typing import List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


def md5_encrypt(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def validate_not_empty(value: str, field_name: str = "输入") -> bool:
    if not value or not value.strip():
        logger.warning(f"{field_name}不能为空！")
        return False
    return True


def get_phone_input(
    prompt: str = "请输入手机号: ", max_attempts: int = 3
) -> Optional[str]:
    try:
        return input(prompt).strip()
    except KeyboardInterrupt:
        logger.warning("用户取消输入")
        return None


def get_numeric_choice(
    prompt: str, min_val: int, max_val: int, max_attempts: int = 3
) -> Optional[int]:
    for attempt in range(max_attempts):
        try:
            choice = input(prompt).strip()
            choice_num = int(choice)
            if min_val <= choice_num <= max_val:
                return choice_num
            logger.warning(f"请输入 {min_val}-{max_val} 之间的数字")
            if attempt < max_attempts - 1:
                logger.warning(f"请重试 (剩余尝试次数: {max_attempts - attempt - 1})")
        except ValueError:
            logger.warning("请输入有效的数字")
            if attempt < max_attempts - 1:
                logger.warning(f"请重试 (剩余尝试次数: {max_attempts - attempt - 1})")
        except KeyboardInterrupt:
            logger.warning("用户取消输入")
            return None
    logger.error("选择失败次数过多")
    return None


def get_user_choice_from_list(
    items: List[str], prompt_prefix: str = "请选择", max_attempts: int = 3
) -> Optional[int]:
    for attempt in range(max_attempts):
        try:
            for i, item in enumerate(items, 1):
                logger.info("  {}. {}", i, item)

            choice = input(f"{prompt_prefix} (1-{len(items)}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(items):
                return choice_num
            logger.warning("请输入 1-{} 之间的数字", len(items))
            if attempt < max_attempts - 1:
                logger.warning(f"请重试 (剩余尝试次数: {max_attempts - attempt - 1})")
        except ValueError:
            logger.warning("请输入有效的数字")
            if attempt < max_attempts - 1:
                logger.warning(f"请重试 (剩余尝试次数: {max_attempts - attempt - 1})")
        except KeyboardInterrupt:
            logger.warning("用户取消操作")
            return None
    logger.error("选择失败次数过多")
    return None

