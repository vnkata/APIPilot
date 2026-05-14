from dataclasses import dataclass

@dataclass
class TUITheme:
    primary: str = "cyan"
    secondary: str = "blue"
    accent: str = "magenta"
    text: str = "white"
    text_dim: str = "dim"
    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    info: str = "cyan"

    symbol_success: str = "[OK]"
    symbol_error: str = "[X]"
    symbol_warning: str = "[!]"
    symbol_info: str = "[*]"
    symbol_progress: str = ">>"
    symbol_bullet: str = "[>]"

    symbol_success_color: str = "green"
    symbol_error_color: str = "red"
    symbol_warning_color: str = "yellow"
    symbol_info_color: str = "cyan"
    symbol_progress_color: str = "cyan"
    symbol_bullet_color: str = "blue"

    status_2xx: str = "green"
    status_3xx: str = "cyan"
    status_4xx: str = "yellow"
    status_5xx: str = "red"
    status_unknown: str = "dim"

    progress_complete: str = "cyan"
    progress_remaining: str = "dim"

    def get_status_color(self, code: int) -> str:
        if 200 <= code < 300:
            return self.status_2xx
        elif 300 <= code < 400:
            return self.status_3xx
        elif 400 <= code < 500:
            return self.status_4xx
        elif 500 <= code < 600:
            return self.status_5xx
        return self.status_unknown

DEFAULT_THEME = TUITheme()