from django import forms
from .models import Setting

class SettingForm(forms.ModelForm):
    class Meta:
        model = Setting
        fields = ['value']

    def clean_value(self):
        """
        Custom validation for the value based on data type
        """
        value = self.cleaned_data['value']
        data_type = self.instance.data_type

        try:
            if data_type == 'int':
                return str(int(value))
            elif data_type == 'float':
                return str(float(value))
            elif data_type == 'bool':
                return str(value).lower() in ['true', '1', 'yes', 'false', '0', 'no']
            return value
        except ValueError:
            raise forms.ValidationError(f"Invalid {self.instance.get_data_type_display()} value")