from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

KERALA_DISTRICTS = [
    'Thiruvananthapuram', 'Kollam', 'Pathanamthitta', 'Alappuzha', 'Kottayam',
    'Idukki', 'Ernakulam', 'Thrissur', 'Palakkad', 'Malappuram',
    'Kozhikode', 'Wayanad', 'Kannur', 'Kasaragod',
]

gst_validator = RegexValidator(
    regex=r'^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$',
    message='Enter a valid 15 character GSTIN in capital letters.',
)


class Shop(models.Model):
    name = models.CharField('Shop name', max_length=150)
    owner_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    gst_number = models.CharField('GST number', max_length=15, blank=True,
                                  validators=[gst_validator])
    address = models.TextField()
    district = models.CharField(max_length=50, choices=[(d, d) for d in KERALA_DISTRICTS])
    pincode = models.CharField(max_length=6, blank=True)
    route = models.ForeignKey('accounts.Route', on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='shops')
    salesman = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='shops', limit_choices_to={'role': 'salesman'},
        help_text='ഈ shop-ന്റെ order എടുക്കുന്ന salesman',
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='shop', limit_choices_to={'role': 'shop'},
        help_text='Shop-ന് login വേണമെങ്കിൽ മാത്രം (role = Shop)',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.district})'