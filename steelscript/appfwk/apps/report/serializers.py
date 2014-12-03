from rest_framework import serializers
from steelscript.appfwk.apps.report.models import Report, Widget


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ('id', 'title', 'slug')


class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
