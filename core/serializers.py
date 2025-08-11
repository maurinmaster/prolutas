# core/serializers.py

from rest_framework import serializers

class PerguntaIASerializer(serializers.Serializer):
    """ Serializer para validar a pergunta enviada pelo usuário. """
    question = serializers.CharField(max_length=500, trim_whitespace=True)