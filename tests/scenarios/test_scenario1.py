# coding: spec

from attrs import define, field
from functools import partial
import typing as tp
import pytest
import strcs

reg = strcs.CreateRegister()
creator = partial(strcs.CreatorDecorator, reg)


@define
class Project:
    details: tp.List["Detail"] = field(factory=lambda: [])


@define
class Detail:
    project: Project
    key: str
    value: tp.Any


@define
class Projects:
    projects: tp.List[Project] = field(factory=lambda: [])


@creator(Projects)
def create_projects(projects: Projects | tp.List | tp.Dict, /) -> strcs.ConvertResponse:
    if isinstance(projects, list):
        return {"projects": projects}
    elif isinstance(projects, dict) and "projects" in projects:
        return {"projects": projects["projects"]}


@creator(Project)
def create_project(
    project: Project | tp.Dict,
    /,
    _meta: strcs.Meta,
    _register: strcs.CreateRegister,
):
    if isinstance(project, dict):
        details = []
        if "details" in project:
            details = project.pop("details")

        project = yield project

        for detail in details:
            project.details.append(
                _register.create(Detail, detail, meta=_meta.clone({"project": project}))
            )


@creator(Detail)
def create_detail(detail: Detail | tp.Dict, /, project: Project) -> strcs.ConvertResponse:
    if isinstance(detail, dict):
        detail["project"] = project
        return detail


describe "Making the projects":

    @pytest.mark.parametrize(
        "config",
        [
            [
                {"details": [{"key": "one", "value": 1}, {"key": "two", "value": 2}]},
                {"details": [{"key": "three", "value": 3}, {"key": "four", "value": 4}]},
            ],
            {
                "projects": [
                    {"details": [{"key": "one", "value": 1}, {"key": "two", "value": 2}]},
                    {"details": [{"key": "three", "value": 3}, {"key": "four", "value": 4}]},
                ]
            },
        ],
    )
    it "can make from a dictionary or list", config:
        projects = reg.create(Projects, config)

        assert isinstance(projects, Projects)
        assert len(projects.projects) == 2
        assert all(isinstance(p, Project) for p in projects.projects)

        project1 = projects.projects[0]
        project2 = projects.projects[1]

        assert projects.projects[0].details[0].project is project1
        assert projects.projects[0].details[1].project is project1

        assert projects.projects[1].details[0].project is project2
        assert projects.projects[1].details[1].project is project2
