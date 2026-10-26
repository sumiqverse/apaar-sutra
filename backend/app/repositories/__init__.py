"""Repositories package exports."""

from app.repositories.base import BaseRepository
from app.repositories.student_repo import StudentRepository

__all__ = ["BaseRepository", "StudentRepository"]
