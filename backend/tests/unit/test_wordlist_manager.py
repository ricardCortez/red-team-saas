"""Unit tests for WordlistManager"""
import os
import tempfile
import pytest
from app.core.wordlist_manager import WordlistManager


@pytest.fixture
def tmp_manager(tmp_path):
    return WordlistManager(custom_dir=str(tmp_path))


class TestWordlistManagerInit:
    def test_creates_custom_dir(self, tmp_path):
        custom = tmp_path / "wordlists"
        assert not custom.exists()
        WordlistManager(custom_dir=str(custom))
        assert custom.exists()

    def test_default_instance(self):
        manager = WordlistManager()
        assert manager.custom_dir is not None


class TestWordlistManagerSystemWordlists:
    def test_list_system_wordlists_returns_list(self):
        manager = WordlistManager()
        result = manager.list_system_wordlists()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_system_entries_have_required_fields(self):
        manager = WordlistManager()
        for entry in manager.list_system_wordlists():
            assert "name" in entry
            assert "path" in entry
            assert "available" in entry
            assert "type" in entry
            assert entry["type"] == "system"

    def test_get_system_path_nonexistent(self):
        manager = WordlistManager()
        result = manager.get_system_path("rockyou")
        # Only returns path if file actually exists on the system
        # On dev machines it may not exist
        assert result is None or isinstance(result, str)

    def test_get_system_path_unknown_name_returns_none(self):
        manager = WordlistManager()
        assert manager.get_system_path("nonexistent_wordlist") is None


class TestWordlistManagerCustomWordlists:
    def test_save_custom_wordlist(self, tmp_manager):
        path = tmp_manager.save_custom_wordlist("test", ["word1", "word2", "word3"])
        assert os.path.isfile(path)

    def test_saved_wordlist_contains_words(self, tmp_manager):
        words = ["password", "admin", "root", "secret"]
        path = tmp_manager.save_custom_wordlist("mylist", words)
        with open(path) as f:
            content = f.read()
        for word in words:
            assert word in content

    def test_txt_extension_added_if_missing(self, tmp_manager):
        path = tmp_manager.save_custom_wordlist("noext", ["word"])
        assert path.endswith(".txt")

    def test_list_custom_wordlists_empty(self, tmp_manager):
        result = tmp_manager.list_custom_wordlists()
        assert result == []

    def test_list_custom_wordlists_after_save(self, tmp_manager):
        tmp_manager.save_custom_wordlist("list1", ["a", "b"])
        tmp_manager.save_custom_wordlist("list2", ["c", "d"])
        result = tmp_manager.list_custom_wordlists()
        names = [r["name"] for r in result]
        assert "list1.txt" in names
        assert "list2.txt" in names

    def test_list_custom_has_required_fields(self, tmp_manager):
        tmp_manager.save_custom_wordlist("check", ["word"])
        result = tmp_manager.list_custom_wordlists()
        assert len(result) == 1
        entry = result[0]
        assert "name" in entry
        assert "path" in entry
        assert "word_count" in entry
        assert "size_bytes" in entry
        assert entry["type"] == "custom"

    def test_delete_custom_wordlist(self, tmp_manager):
        tmp_manager.save_custom_wordlist("todelete", ["x"])
        deleted = tmp_manager.delete_custom_wordlist("todelete")
        assert deleted is True
        assert tmp_manager.list_custom_wordlists() == []

    def test_delete_nonexistent_returns_false(self, tmp_manager):
        assert tmp_manager.delete_custom_wordlist("ghost") is False

    def test_save_cewl_output(self, tmp_manager):
        words = ["login", "password", "admin"]
        path = tmp_manager.save_cewl_output("target", words)
        assert "cewl_target" in path
        assert os.path.isfile(path)

    def test_list_all_returns_dict(self, tmp_manager):
        result = tmp_manager.list_all()
        assert "system" in result
        assert "custom" in result
        assert isinstance(result["system"], list)
        assert isinstance(result["custom"], list)

    def test_sanitize_filename_special_chars(self, tmp_manager):
        path = tmp_manager.save_custom_wordlist("bad/../name!@#", ["word"])
        # Should not raise, and should produce valid file
        assert os.path.isfile(path)


class TestWordlistManagerWordCount:
    def test_word_count_in_listing(self, tmp_manager):
        words = ["one", "two", "three", "four", "five"]
        tmp_manager.save_custom_wordlist("count_test", words)
        listing = tmp_manager.list_custom_wordlists()
        assert listing[0]["word_count"] == 5
