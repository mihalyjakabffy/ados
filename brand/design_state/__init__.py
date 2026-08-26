"""
brand/design_state/

ADOS-M2.5 — the design-state-centric root of ADOS.

``brand.design_state.model.DesignState`` is a *read model*: a single,
serializable snapshot assembled from the real, existing domain objects
(``brand.project.model.Project``/``Document``, ``brand.models.brand.Brand``,
``brand.creative.plan.PagePlan``, ``brand.creative.direction.CreativeDirection``,
``brand.project.requirements``), never a second place any of that data is
actually stored. See ``brand/design_state/build.py``'s module docstring
for why, and ``docs/architecture/m2.5-design-state.md`` for the full
picture.
"""
