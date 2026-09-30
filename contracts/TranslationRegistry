# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import re

from genlayer import *
from dataclasses import dataclass


def clean_url(url: str):
    if not url:
        return None
    cleaned = url.strip().rstrip('/')
    if cleaned.startswith('http://'):
        cleaned = cleaned.replace('http://', 'https://', 1)
    cleaned = cleaned.replace(' ', '')
    if '?' in cleaned:
        cleaned = cleaned.split('?')[0]
    return cleaned if cleaned else None


def is_valid_url(url: str) -> bool:
    pattern = re.compile(
        r'^(https?://)'
        r'([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'
        r'(/[\w\-./?%&=]*)?$'
    )
    return bool(pattern.match(url.strip()))


@allow_storage
@dataclass
class TranslationRecord:
    translation_id: u256
    translator: str
    source_url: str
    target_lang: str
    translated_text: str
    status: str  # SUBMITTED


class TranslationRegistry(gl.Contract):
    translations: TreeMap[u256, TranslationRecord]
    next_id: u256

    def __init__(self):
        self.next_id = u256(0)

    @gl.public.write
    def submit_translation(self, source_url: str, target_lang: str, translated_text: str) -> u256:
        cleaned = clean_url(source_url)
        assert cleaned is not None, f"Invalid source URL: {source_url}"
        assert is_valid_url(cleaned), f"Invalid source URL: {cleaned}"
        assert target_lang.strip() != "", "Target language cannot be empty"
        assert translated_text.strip() != "", "Translated text cannot be empty"

        tid = self.next_id
        self.next_id += u256(1)
        self.translations[tid] = TranslationRecord(
            translation_id=tid,
            translator=str(gl.message.sender_address),
            source_url=cleaned,
            target_lang=target_lang.strip(),
            translated_text=translated_text,
            status="SUBMITTED",
        )
        return tid

    @gl.public.view
    def get_translation_status(self, translation_id: u256) -> str:
        if translation_id not in self.translations:
            return "NOT_FOUND"
        return self.translations[translation_id].status

    @gl.public.view
    def get_translation_data(self, translation_id: u256) -> str:
        if translation_id not in self.translations:
            return "NOT_FOUND"
        t = self.translations[translation_id]
        return json.dumps({
            "translation_id": int(t.translation_id),
            "translator": t.translator,
            "source_url": t.source_url,
            "target_lang": t.target_lang,
            "translated_text": t.translated_text,
            "status": t.status,
        })

    @gl.public.view
    def list_translations(self) -> str:
        items = []
        for key in self.translations:
            t = self.translations[key]
            items.append(f"{int(t.translation_id)}:{t.status}")
        return ",".join(items)

    @gl.public.view
    def get_translator_submissions(self, translator: str) -> str:
        items = []
        for key in self.translations:
            t = self.translations[key]
            if t.translator == translator:
                items.append(str(int(t.translation_id)))
        return ",".join(items)
