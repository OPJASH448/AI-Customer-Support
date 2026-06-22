# Generated migration — replaces local FileField with Supabase Storage URL fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('support', '0005_documentchunk_docchunk_embed_hnsw_idx'),
    ]

    operations = [
        # Remove the old local FileField (media/ on disk)
        migrations.RemoveField(
            model_name='document',
            name='file',
        ),
        # Add Supabase Storage URL
        migrations.AddField(
            model_name='document',
            name='file_url',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=500,
                help_text='Supabase Storage public/signed URL for the original file',
            ),
        ),
        # Add original filename for display purposes
        migrations.AddField(
            model_name='document',
            name='original_filename',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=255,
                help_text='Original uploaded filename (e.g. report.pdf)',
            ),
        ),
    ]
