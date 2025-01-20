import rich.progress as rp



class NestedProgress(rp.Progress):
    """
    Allow to have nested `rich.Progress` bars with *different* layout.
    Code originating from https://github.com/Textualize/rich/discussions/950
    """
    def get_renderables(self):
        for task in self.tasks:
            if task.fields.get("progress_type") == "patient":
                self.columns = [
                        rp.SpinnerColumn("line"),
                        rp.TextColumn("[green]{task.description}[/]"),
                        rp.BarColumn(), rp.TaskProgressColumn(),
                        rp.TextColumn("[green]patients[/][bold] • [/]"),
                        rp.TimeRemainingColumn(elapsed_when_finished=True)
                        ]
            if task.fields.get("progress_type") == "voxel":
                self.columns = [
                        rp.TextColumn("    "), rp.SpinnerColumn("point"),
                        rp.TextColumn("[green]{task.description}[/]"),
                        rp.BarColumn(), rp.TaskProgressColumn(),
                        rp.TextColumn("[green]meshes[/][bold] • [/]"),
                        rp.TimeRemainingColumn(elapsed_when_finished=True)
                        ]
            yield self.make_tasks_table([task])
