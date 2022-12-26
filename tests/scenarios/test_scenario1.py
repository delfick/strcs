# coding: spec

import typing as tp

import pytest
from attrs import define, field

import strcs

reg = strcs.CreateRegister()
creator = reg.make_decorator()


@define
class Project:
    details: tp.List["Detail"] = field(factory=lambda: [])


@define
class Detail:
    project: Project
    key: str
    value: object


@define
class Projects:
    projects: tp.List[Project] = field(factory=lambda: [])


@creator(Projects)
def create_projects(value: object) -> dict | None:
    if isinstance(value, list):
        return {"projects": value}
    elif isinstance(value, dict) and "projects" in value:
        return {"projects": value["projects"]}

    return None


@creator(Project)
def create_project(
    value: object,
    /,
    _meta: strcs.Meta,
    _register: strcs.CreateRegister,
) -> tp.Generator[dict, Project, None]:
    if isinstance(value, dict):
        details = []
        if "details" in value:
            details = value.pop("details")

        project = yield value

        for detail in details:
            project.details.append(
                _register.create(Detail, detail, meta=_meta.clone({"project": project}))
            )

    return None


@creator(Detail)
def create_detail(value: object, /, project: Project) -> dict | None:
    if not isinstance(value, dict):
        return None

    value["project"] = project
    return value


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
