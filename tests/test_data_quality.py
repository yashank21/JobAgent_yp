from app.models.job import Job
from app.services.data_quality import (
    measure_source_quality,
    quality_class,
    render_quality_report,
)


def make_job(source, description_status, skills_status, experience_status, length=0):
    return Job(
        id=source,
        title="Engineer",
        company="Example",
        source=source,
        description_status=description_status,
        skills_status=skills_status,
        experience_status=experience_status,
        description_length=length,
    )


def test_quality_report_aggregates_by_source():
    reports = measure_source_quality([
        make_job("ashby", "present", "extracted", "none_found", 100),
        make_job("ashby", "absent", "not_attempted", "not_attempted"),
        make_job("workday", "retrieval_failed", "not_attempted", "not_attempted"),
    ])

    ashby = reports["ashby"]
    assert ashby.jobs_analyzed == 2
    assert ashby.descriptions_present == 1
    assert ashby.skills_extracted == 1
    assert ashby.average_description_length == 100
    assert reports["workday"].retrieval_failures == 1


def test_quality_rendering_keeps_denominators():
    text = render_quality_report([
        make_job("ashby", "present", "none_found", "none_found", 80),
    ])

    assert "JD present: 1/1 (100.0%)" in text
    assert "No recognized skills: 1/1 (100.0%)" in text


def test_quality_classes_distinguish_retrieval_and_partial_extraction():
    assert quality_class(
        make_job("workday", "retrieval_failed", "not_attempted", "not_attempted")
    ) == "D - retrieval failure"
    assert quality_class(
        make_job("ashby", "present", "extracted", "none_found", 80)
    ) == "B - partial extraction"


def test_quality_measurement_reports_description_extremes():
    report = measure_source_quality([
        make_job("greenhouse", "present", "extracted", "extracted", 10),
        make_job("greenhouse", "present", "extracted", "none_found", 30),
    ])["greenhouse"]

    assert report.minimum_description_length == 10
    assert report.maximum_description_length == 30