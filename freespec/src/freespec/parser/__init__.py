"""Parser module for .spec files."""

from freespec.parser.dependency import DependencyResolver
from freespec.parser.models import DependencyGraph, Section, SpecFile
from freespec.parser.spec_parser import SpecParser

__all__ = ["DependencyGraph", "DependencyResolver", "Section", "SpecFile", "SpecParser"]
