from collections.abc import Generator
from typing import Generic, TypeVar

import attrs
import pytest

import strcs

reg = strcs.CreateRegister()
creator = reg.make_decorator()

T = TypeVar("T")


@attrs.define
class Project:
    details: list["Detail"] = attrs.field(factory=lambda: [])


@attrs.define
class Detail:
    project: Project
    key: str
    value: object


@attrs.define
class Item:
    one: int
    two: int


@attrs.define
class ItemOne(Item):
    one: int = 20
    two: int = 50
    three: bool = False


@attrs.define
class ItemTwo(Item):
    one: int = 3
    two: int = 5
    four: bool = True


@attrs.define
class Container(Generic[T]):
    category: str
    item: T


@attrs.define
class Projects:
    projects: list[Project] = attrs.field(factory=lambda: [])


@creator(Item)
def create_item(item: object, /) -> dict | None:
    if item is strcs.NotSpecified:
        item = {}
    if isinstance(item, dict):
        return item
    return None


categories: dict[str, type[Item]] = {"one": ItemOne, "two": ItemTwo}


@creator(Container)
def create_container(
    item: object, want: strcs.Type[Container], /, _register: strcs.CreateRegister
) -> dict | None:
    if not isinstance(item, dict):
        return None

    (expected,) = want.find_generic_subtype(Item)
    assert expected is not None
    if "category" not in item:
        return None
    using = categories.get(item["category"])
    assert expected.is_equivalent_type_for(using), f"Expected {using} to be an {expected}"

    item["item"] = _register.create(using, item.get("item", strcs.NotSpecified))
    return item


@creator(Projects)
def create_projects(value: object, /) -> dict | None:
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
) -> Generator[dict, Project]:
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


class TestMakingTheProjects:
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
    def test_it_can_make_from_a_dictionary_or_list(self, config):
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

    def test_it_can_make_generic_types(self):
        container = reg.create(Container[ItemOne], {"category": "one"})
        assert isinstance(container.item, ItemOne)
        assert container.item.one == 20
        assert container.item.two == 50
        assert not container.item.three

        container2 = reg.create(Container[ItemTwo], {"category": "two"})
        assert isinstance(container2.item, ItemTwo)
        assert container2.item.one == 3
        assert container2.item.two == 5
        assert container2.item.four

    def test_it_can_complain_about_asking_for_the_wrong_subtype(self):
        with pytest.raises(strcs.errors.UnableToConvert) as e:
            reg.create(Container[ItemOne], {"category": "two"})

        assert (
            str(e.value.error).split("\n")[0]
            == "Expected <class 'tests.scenarios.test_scenario1.ItemTwo'> to be an <class 'tests.scenarios.test_scenario1.ItemOne'>"
        )

    def test_it_can_complain_about_not_asking_for_a_subtype(self):
        with pytest.raises(strcs.errors.UnableToConvert) as e:
            reg.create(Container)

        assert e.value.reason == "Converter didn't return a value to use"
