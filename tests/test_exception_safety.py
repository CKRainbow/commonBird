import json
import os
from pathlib import Path

import pytest

import src.utils.location as location
from src.utils.api_exceptions import ApiErrorBase, DataFileError
from src.utils.files import read_json, write_json
from src.utils.taxon import convert_taxon_z4_ebird, process_loc


# ---------- 本地文件读写 ----------


def test_read_json_missing_file_returns_default(tmp_path: Path):
    assert read_json(tmp_path / "nope.json") is None
    assert read_json(tmp_path / "nope.json", default={}) == {}


def test_read_json_corrupt_file_returns_default(tmp_path: Path):
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert read_json(broken, default={"fallback": True}) == {"fallback": True}


def test_write_json_creates_file_and_backup(tmp_path: Path):
    target = tmp_path / "data.json"
    write_json(target, {"v": 1})
    assert json.loads(target.read_text(encoding="utf-8")) == {"v": 1}

    # 第二写入会把旧文件备份成 .bak（旧文件缺失时也不应报错）
    write_json(target, {"v": 2}, backup=True)
    assert json.loads(target.read_text(encoding="utf-8")) == {"v": 2}
    assert json.loads((tmp_path / "data.json.bak").read_text(encoding="utf-8")) == {
        "v": 1
    }


def test_write_json_reports_error_as_data_file_error(tmp_path: Path, monkeypatch):
    def boom(*args, **kwargs):
        raise PermissionError("拒绝访问")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(DataFileError) as excinfo:
        write_json(tmp_path / "data.json", {"v": 1})
    assert "data.json" in str(excinfo.value)


def test_api_error_str_is_readable():
    # 旧实现只把 message 存到属性里，str(e) 是空串，界面上提示会变成“失败: ”
    assert str(DataFileError("无法写入 x.json")) == "无法写入 x.json"
    assert isinstance(DataFileError("x"), ApiErrorBase)


# ---------- 并发批量大小 ----------


@pytest.mark.parametrize("cpu_count,expected", [(1, 1), (2, 1), (8, 4)])
def test_batch_size_never_zero(monkeypatch, cpu_count, expected):
    monkeypatch.setattr(location.multiprocessing, "cpu_count", lambda: cpu_count)
    assert location._batch_size() == expected


# ---------- 地点代码转换 ----------


def test_process_loc_unknown_province_does_not_raise():
    assert process_loc("XX-01") == "XX-01"
    assert process_loc("SH") == "上海市"


# ---------- Z4 -> eBird 学名转换 ----------


def test_convert_taxon_handles_missing_fields():
    report = {"obs": [{"latinname": "Aegithalos concinnus"}], "province_name": "浙江省"}
    convert_taxon_z4_ebird(report, {})
    assert report["obs"][0]["latinname"] == "Aegithalos concinnus"


def test_convert_taxon_skips_time_rules_when_date_malformed():
    taxon_map = {"Old name": [{"name": "New name", "time": "1-3"}]}
    report = {
        "obs": [{"latinname": "Old name"}],
        "province_name": "浙江省",
        "start_time": "未知时间",
    }
    convert_taxon_z4_ebird(report, taxon_map)
    # 无法判断月份时不应盲替换
    assert report["obs"][0]["latinname"] == "Old name"


def test_convert_taxon_applies_plain_mapping():
    taxon_map = {"Old name": "New name"}
    report = {
        "obs": [{"latinname": "Old name"}],
        "province_name": "浙江省",
        "start_time": "2025-11-08 08:25:00",
    }
    convert_taxon_z4_ebird(report, taxon_map)
    assert report["obs"][0]["latinname"] == "New name"
