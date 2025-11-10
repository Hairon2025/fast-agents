import importlib
import pkgutil
from fastapi import APIRouter, FastAPI
import logging
from app.config import settings

logger = logging.getLogger(__name__)

def auto_register_routers(app: FastAPI, package_name: str = "app.api.endpoints"):
    """
    自动注册路由
    
    Args:
        app: FastAPI应用实例
        package_name: 包含路由的包名
    """
    try:
        package = importlib.import_module(package_name)
    except ImportError as e:
        logger.error(f"无法导入包 {package_name}: {e}")
        return
    
    routers_found = 0
    
    # 遍历包中的所有模块
    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
        if is_pkg:
            # 如果是子包，递归处理
            sub_package_name = f"{package_name}.{module_name}"
            routers_found += auto_register_routers_from_package(app, sub_package_name)
        else:
            # 如果是模块，尝试导入并注册路由
            full_module_name = f"{package_name}.{module_name}"
            routers_found += register_router_from_module(app, full_module_name)
    
    logger.info(f"自动注册了 {routers_found} 个路由模块")

def auto_register_routers_from_package(app: FastAPI, package_name: str) -> int:
    """从包中自动注册路由"""
    routers_found = 0
    try:
        package = importlib.import_module(package_name)
    except ImportError as e:
        logger.warning(f"无法导入包 {package_name}: {e}")
        return 0
    
    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
        if not is_pkg:
            full_module_name = f"{package_name}.{module_name}"
            routers_found += register_router_from_module(app, full_module_name)
    
    return routers_found

def register_router_from_module(app: FastAPI, module_name: str) -> int:
    """从模块注册路由"""
    try:
        module = importlib.import_module(module_name)
        
        # 查找模块中的 router 变量
        if hasattr(module, 'router') and isinstance(getattr(module, 'router'), APIRouter):
            router = getattr(module, 'router')
            
            # 根据模块名确定路由前缀和标签
            prefix, tags = get_router_config(module_name)
            
            # 注册路由
            app.include_router(router, prefix=prefix, tags=tags)
            logger.info(f"注册路由: {module_name} -> {prefix} [{tags}]")
            return 1
            
    except ImportError as e:
        logger.warning(f"无法导入模块 {module_name}: {e}")
    except Exception as e:
        logger.warning(f"注册路由时出错 {module_name}: {e}")
    
    return 0

def get_router_config(module_name: str) -> tuple[str, list[str]]:
    """
    根据模块名获取路由配置
    
    Returns:
        tuple: (prefix, tags)
    """
    # 从模块名中提取最后一部分作为标签
    module_parts = module_name.split('.')
    module_base_name = module_parts[-1]
    
    # 特殊模块处理
    if module_base_name == 'health':
        prefix = f"{settings.API_PREFIX}"
        tags = ["health"]
    elif module_base_name == 'users':
        prefix = f"{settings.API_PREFIX}/users"
        tags = ["users"]
    else:
        # 默认配置：使用模块名作为标签和路径
        prefix = f"{settings.API_PREFIX}/{module_base_name}"
        tags = [module_base_name]
    
    return prefix, tags