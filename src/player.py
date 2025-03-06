"""
This module defines the Player and Attributes classes for managing player 
info, including their attributes such as shooting, dribbling, passing, tackling, 
fitness, and goalkeeping. The overall rating is calculated based on attributes 
and current form.
"""

from dataclasses import dataclass

__all__ = [
    "Shooting",
    "Dribbling",
    "Passing",
    "Tackling",
    "Fitness",
    "Goalkeeping",
    "Attributes",
    "Player",
]

NUM_ATTRIBUTES = 6


@dataclass
class PlayerAttribute:
    """
    A base class for player attributes that contains a score and provides access
    to it.
    """

    score: float

    def __post_init__(self):
        if not isinstance(self.score, (int, float)):
            raise ValueError(f"Invalid score: {self.score}. Must be numeric.")

    def get_score(self) -> float:
        return self.score


class Shooting(PlayerAttribute):
    """Represents a player's shooting ability."""

    pass


class Dribbling(PlayerAttribute):
    """Represents a player's dribbling ability."""

    pass


class Passing(PlayerAttribute):
    """Represents a player's passing ability."""

    pass


class Tackling(PlayerAttribute):
    """Represents a player's tackling ability."""

    pass


class Fitness(PlayerAttribute):
    """Represents a player's fitness level."""

    pass


class Goalkeeping(PlayerAttribute):
    """Represents a player's goalkeeping ability."""

    pass


@dataclass
class Attributes:
    """
    Groups all of a player's attributes into a single dataclass.
    """

    shooting: Shooting
    dribbling: Dribbling
    passing: Passing
    tackling: Tackling
    fitness: Fitness
    goalkeeping: Goalkeeping

    @classmethod
    def from_values(cls, values: dict[str, float]) -> "Attributes":
        for key, value in values.items():
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Invalid value for {key}: {value}. Must be numeric."
                )

        return cls(
            shooting=Shooting(values.get("shooting", 65)),
            dribbling=Dribbling(values.get("dribbling", 65)),
            passing=Passing(values.get("passing", 65)),
            tackling=Tackling(values.get("tackling", 65)),
            fitness=Fitness(values.get("fitness", 65)),
            goalkeeping=Goalkeeping(values.get("goalkeeping", 65)),
        )


@dataclass
class Player:
    """
    Represents a player with a name, attributes, and form.
    The overall rating is computed from base attributes and current form.
    """

    name: str
    attributes: Attributes
    form: int  # Form scale 0-10, where 5 is average

    def __post_init__(self):
        # Clamp form between 0 and 10
        self.form = max(0, min(self.form, 10))

    def _get_base_rating(self) -> float:
        """
        Compute base rating as the average of all player attributes.
        """
        total_rating = sum(
            getattr(self.attributes, attr).get_score()
            for attr in vars(self.attributes)
        )
        return total_rating / NUM_ATTRIBUTES

    def get_overall_rating(self) -> float:
        """
        Calculates the overall rating by applying a form multiplier to the base
        rating.

        The multiplier is 1 + 0.05 * (form - 5). That is, form 5 is neutral.
        """
        base_rating = self._get_base_rating()
        multiplier = 1 + 0.05 * (self.form - 5)
        return base_rating * multiplier

    def update_form(self, won: bool) -> None:
        """
        Updates the player's form based on the outcome of a match.
        Increase form if won, decrease if lost.
        """
        if won:
            self.form = min(self.form + 1, 10)
        else:
            self.form = max(self.form - 1, 0)
