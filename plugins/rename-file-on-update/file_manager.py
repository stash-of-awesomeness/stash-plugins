class StashFile:
    def __init__(self, config, scene_data, file_path):
        self.config = config
        self.scene_data = scene_data
        self.file_path = file_path

    def get_old_file_path(self):
        return self.file_path

    def get_new_file_path(self):
        pass

    def rename_file(self):
        pass
