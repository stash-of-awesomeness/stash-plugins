class Config:
    DEFAULT_CONFIG = {
        "defaultDirectoryPathFormat": "",
        "defaultFileNameFormat": "",
        "dryRun": False,
        "renameUnorganized": False,
    }

    def __init__(self, config):
        self.config = config

    def __getattr__(self, name):
        config_name = self.__to_camel_case(name)

        return self.config.get(config_name, Config.DEFAULT_CONFIG.get(config_name))

    def __to_camel_case(snake_str):
        pascal_case = "".join(x.capitalize() for x in snake_str.lower().split("_"))
        return pascal_case[0].lower() + pascal_case[1:]
