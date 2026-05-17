"""The four named attack patterns.

Each module exposes an ``async generate_<pattern>(client, nl, original_spec,
language) -> AttackResult``. :data:`ATTACK_FUNCS` maps an
:class:`~trojanspec.schemas.AttackPattern` to its generator.
"""

from trojanspec.generators.attacks.base import AttackResult
from trojanspec.generators.attacks.domain_restriction import generate_domain_restriction
from trojanspec.generators.attacks.implementation_leak import generate_implementation_leak
from trojanspec.generators.attacks.predicate_swap import generate_predicate_swap
from trojanspec.generators.attacks.vacuity import generate_vacuity
from trojanspec.schemas import AttackPattern

ATTACK_FUNCS = {
    AttackPattern.VACUITY: generate_vacuity,
    AttackPattern.IMPLEMENTATION_LEAK: generate_implementation_leak,
    AttackPattern.DOMAIN_RESTRICTION: generate_domain_restriction,
    AttackPattern.PREDICATE_SWAP: generate_predicate_swap,
}

__all__ = [
    "ATTACK_FUNCS",
    "AttackResult",
    "generate_domain_restriction",
    "generate_implementation_leak",
    "generate_predicate_swap",
    "generate_vacuity",
]
