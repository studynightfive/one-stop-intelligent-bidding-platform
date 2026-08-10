"""片段库内存仓储；持久化适配器合入前供领域测试和 Demo 使用。"""

from __future__ import annotations

import copy

from app.domains.bids.errors import not_found
from app.domains.fragments.entities import (
    FragmentEntity,
    FragmentReferenceEntity,
    FragmentVersionEntity,
)


class FragmentStore:
    def __init__(self) -> None:
        self.fragments: dict[str, FragmentEntity] = {}
        self.versions: dict[str, FragmentVersionEntity] = {}
        self.references: dict[str, FragmentReferenceEntity] = {}

    def save(self, fragment: FragmentEntity) -> FragmentEntity:
        self.fragments[fragment.id] = copy.deepcopy(fragment)
        return copy.deepcopy(fragment)

    def get(self, fragment_id: str, *, tenant_id: str) -> FragmentEntity:
        fragment = self.fragments.get(fragment_id)
        if fragment is None or fragment.tenant_id != tenant_id or fragment.deleted_at is not None:
            raise not_found("片段不存在", fragmentId=fragment_id)
        return copy.deepcopy(fragment)

    def list_active(self, *, tenant_id: str, category: str | None = None) -> list[FragmentEntity]:
        category_key = category.casefold() if category else None
        items = [
            copy.deepcopy(fragment)
            for fragment in self.fragments.values()
            if fragment.tenant_id == tenant_id
            and fragment.deleted_at is None
            and (category_key is None or fragment.category.casefold() == category_key)
        ]
        return items

    def save_version(self, version: FragmentVersionEntity) -> FragmentVersionEntity:
        self.versions[version.id] = copy.deepcopy(version)
        return copy.deepcopy(version)

    def next_version_number(self, fragment_id: str) -> int:
        numbers = [item.version_number for item in self.versions.values() if item.fragment_id == fragment_id]
        return max(numbers, default=0) + 1

    def list_versions(self, *, tenant_id: str, fragment_id: str) -> list[FragmentVersionEntity]:
        items = [
            copy.deepcopy(version)
            for version in self.versions.values()
            if version.tenant_id == tenant_id and version.fragment_id == fragment_id
        ]
        return sorted(items, key=lambda item: item.version_number)

    def save_reference(self, reference: FragmentReferenceEntity) -> FragmentReferenceEntity:
        self.references[reference.id] = copy.deepcopy(reference)
        return copy.deepcopy(reference)

    def list_references(self, *, tenant_id: str, fragment_id: str) -> list[FragmentReferenceEntity]:
        return [
            copy.deepcopy(reference)
            for reference in self.references.values()
            if reference.tenant_id == tenant_id and reference.fragment_id == fragment_id
        ]
