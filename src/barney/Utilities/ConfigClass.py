from __future__ import annotations

import dataclasses
import json
import logging
import pprint
from pathlib import Path
from typing import TYPE_CHECKING

from qtpy.QtCore import QStandardPaths

if TYPE_CHECKING:
    from typing import Any, Dict, List, Set


logger = logging.getLogger(__name__)
pformat = pprint.PrettyPrinter(indent=2).pformat

CONFIG_PATH = Path(QStandardPaths.writableLocation(QStandardPaths.ConfigLocation))
CONFIG_PATH.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_PATH / "barney_config.json"
if not CONFIG_PATH.exists():
    logger.info(f"Config file {CONFIG_FILE.as_posix()} could not be found or created.")
else:
    logger.info(f"Config file at {CONFIG_FILE.as_posix()}")


class ConfigClass:
    # keep track of all children to easily save config file
    children: List[ConfigClass] = []
    # map config_keys to children
    key_map: Dict[str, ConfigClass] = {}
    # dictionary representation of full config file
    meta_config: Dict[str, Dict[str, Any]] = {}
    # set of fields that should not be added to the config file
    config_blacklist: Set[str] = set()

    def __init__(self, config_key: str, *args: Any, **kwargs: Any) -> None:
        if type(self) is ConfigClass:
            raise ValueError("ConfigClass must be subclassed.")
        if not dataclasses.is_dataclass(self):
            raise ValueError("ConfigClass subclass must be a dataclass.")

        # pass along to fellow base classes
        super().__init__(*args, **kwargs)

        if config_key in ConfigClass.key_map:
            logger.warning(f"config_key {config_key} being overwritten.")
        self.config_key = config_key
        ConfigClass.key_map[config_key] = self
        ConfigClass.children.append(self)

        self.resetToBarneyDefaults()
        if CONFIG_FILE.exists():
            self.resetToConfigDefaults()

    def resetToBarneyDefaults(self) -> None:
        """resets config options to Barney's original defaults,
        not config file user defaults"""
        for name, field in self.__dataclass_fields__.items():  # type: ignore
            value = field.default
            if value == dataclasses.MISSING:
                value = field.default_factory()
            setattr(self, name, value)

    def resetToConfigDefaults(self) -> None:
        config = ConfigClass.getConfigDictFor(self.config_key)
        logger.debug(f"Resetting {type(self).__name__} from {pformat(config)}")
        # place Barney defaults up front, this way they will be overwritten by user config
        # but left over if anything goes wrong, either generally or on an individual basis
        self.resetToBarneyDefaults()
        if config:
            self.setConfigFromDict(config)
        else:
            logger.warning("User config not found. Using Barney defaults.")

    def setConfigFromDict(self, config: dict) -> None:
        for key, value in config.items():
            try:
                setattr(self, key, value)
            except Exception as e:
                logger.error(
                    "Exception occured while loading config file.\n"
                    + f"Class: {type(self).__name__}\n"
                    + f"Attr:  {key}\n"
                    + f"Value: {value}\n"
                    + f"Error: {e}\n"
                )

    @staticmethod
    def getConfigDictFor(config_key: str) -> Dict[str, Any]:
        if not ConfigClass.meta_config:
            ConfigClass.getMetaConfigFromFile()
        if config_key in ConfigClass.meta_config:
            return ConfigClass.meta_config[config_key]
        logger.error(
            f'config_key "{config_key}" not found in meta_config keys {ConfigClass.meta_config.keys()}.'
        )
        return {}

    @staticmethod
    def getMetaConfigFromFile() -> Dict[str, Dict[str, Any]]:
        if not CONFIG_FILE.exists():
            logger.error(f"Config file '{CONFIG_FILE}' not found.")
            return {}
        logger.info(f"Loading configs from {CONFIG_FILE.as_posix()}")

        with open(CONFIG_FILE) as cfile:
            try:
                meta_config = json.load(cfile)
            except json.JSONDecodeError:
                logger.error("Invalid Config file")
                meta_config = {}

        logger.debug(f"meta_config found in file: \n{pformat(meta_config)}")
        if not meta_config:
            logger.warning("Meta config empty after reading from file.")

        for _, inner_dict in meta_config.items():
            if type(inner_dict) is not dict:
                logger.error("Invalid config file")
                raise RuntimeError("Invalid config file")

        ConfigClass.meta_config = meta_config
        return meta_config

    @staticmethod
    def jsonDump() -> None:
        logger.info(f"Saving config file: {CONFIG_FILE.as_posix()}")
        meta_config = {}
        for child in ConfigClass.children:
            child_config = {
                k: v
                for k, v in dataclasses.asdict(child).items()
                if k not in ConfigClass.config_blacklist
            }
            meta_config[child.config_key] = child_config

        logger.debug(f"meta config being saved to file: {pformat(meta_config)}")

        with open(CONFIG_FILE, "w") as cfile:
            json.dump(meta_config, cfile)

        ConfigClass.meta_config = meta_config
