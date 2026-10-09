from evren_mcp.explain import STATUS_TR, explain_http, explain_job


def test_disk_full_job_is_platform_side_and_mentions_refund():
    job = {
        "status": "FAILED",
        "error_category": "INFRA",
        "error_message": (
            "HPC dosya yazimi hatasi: [Errno 28] No space left on device: '/tmp/x'\n"
            '--- traceback ---\nFile "/app/app/workers/tasks_training.py"'
        ),
    }
    metin = explain_job(job)
    assert "disk" in metin.lower() and "iade" in metin
    assert "/app/app" not in metin  # iç altyapı ayrıntısı aktarılmaz (#37)


def test_other_failure_shows_only_first_line():
    job = {
        "status": "FAILED",
        "error_category": "USER",
        "error_message": "CUDA out of memory\nsatir2 gizli ayrinti",
    }
    metin = explain_job(job)
    assert "CUDA out of memory" in metin and "satir2" not in metin


def test_running_job_has_no_explanation():
    assert explain_job({"status": "TRAINING"}) is None


def test_terms_and_auth_messages():
    assert "şart" in explain_http(403, "terms_not_accepted", "x").lower()
    assert "anahtar" in explain_http(401, None, "x").lower()
    assert "Bulunamadı" in explain_http(404, "NOT_FOUND", "Veri seti bulunamadı")


def test_status_names_turkish():
    assert "hazırlanıyor" in STATUS_TR["EXPORTING"]
