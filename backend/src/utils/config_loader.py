from pydantic import BaseModel
import yaml

class LLMConfig(BaseModel):
    model: str
    prompt_template: str
    start_page: int = 0

class LLMConfigLoader:
    def __init__(self, config_path: str):
        self._config_path = config_path
        self._config = self.load_config()
        self._verify_prompt_template()

    def load_config(self) -> LLMConfig:
        with open(self._config_path, "r") as file:
            config_data = yaml.safe_load(file)
            return LLMConfig(**config_data)

    def _verify_prompt_template(self):
        """
        Verify that the prompt template contains all required placeholders.
        This is a simple check; you might want to implement more complex validation.
        """
        template = self._config.prompt_template
        required_placeholder = "{pdf_text}"
        if required_placeholder not in template:
            raise ValueError(
                f"Prompt template is missing required placeholder: {required_placeholder}"
            )

    def get_config(self) -> LLMConfig:
        return self._config
