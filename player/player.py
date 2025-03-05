"""
This module defines the `Player` and `Attributes` classes for managing player 
info, including their attributes such as shooting, dribbling, passing, tackling, 
fitness,and goalkeeping. Each attribute is stored as a raw value, and the 
overall rating of the player is calculated using TrueSkill, which dynamically 
adjusts based on performance.

Classes:
    - Shooting: Represents a player's shooting ability as a raw score.
    - Dribbling: Represents a player's dribbling ability as a raw score.
    - Passing: Represents a player's passing ability as a raw score.
    - Tackling: Represents a player's tackling ability as a raw score.
    - Fitness: Represents a player's fitness level as a raw score.
    - Goalkeeping: Represents a player's goalkeeping ability as a raw score.
    - Attributes: Groups all player attributes into a single dataclass.
    - Player: Represents a player with a name, attributes, and form. Provides a 
              method to calculate the player's overall rating using TrueSkill.
"""

from dataclasses import dataclass

import trueskill


@dataclass
class Shooting:
    """
    Represents a player's shooting ability.

    :param score:
        The raw score representing the player's shooting ability out of 100.
    """

    score: float


@dataclass
class Dribbling:
    """
    Represents a player's dribbling ability.

    :param score:
        The raw score representing the player's dribbling ability out of 100.
    """

    score: float


@dataclass
class Passing:
    """
    Represents a player's passing ability.

    :param score:
        The raw score representing the player's passing ability out of 100.
    """

    score: float


@dataclass
class Tackling:
    """
    Represents a player's tackling ability.

    :param score:
        The raw score representing the player's tackling ability out of 100.
    """

    score: float


@dataclass
class Fitness:
    """
    Represents a player's fitness level.

    :param score:
        The raw score representing the player's fitness out of 100.
    """

    score: float


@dataclass
class Goalkeeping:
    """
    Represents a player's goalkeeping ability.

    :param score:
        The raw score representing the player's goalkeeping ability out of 100.
    """

    score: float


@dataclass
class Attributes:
    """
    Groups all of a player's attributes into a single dataclass.

    :param shooting:
        A player's shooting ability.
    :param dribbling:
        A player's dribbling ability.
    :param passing:
        A player's passing ability.
    :param tackling:
        A player's tackling ability.
    :param fitness:
        A player's fitness.
    :param goalkeeping:
        A player's goalkeeping ability.
    """

    shooting: Shooting
    dribbling: Dribbling
    passing: Passing
    tackling: Tackling
    fitness: Fitness
    goalkeeping: Goalkeeping

    @classmethod
    def from_values(cls, values: dict[str, float]) -> "Attributes":
        """
        Create an Attributes class from the passed-in values.

        :param values:
            A dictionary containing player attribute values.
            The dictionary should contain keys for each attribute:
            'shooting', 'dribbling', 'passing', 'tackling', 'fitness',
            and 'goalkeeping'. Each key should have a score value for the
            rating.

        :raises:
            A ValueError if the values are not numeric.

        :return:
            An `Attributes` object with all attributes initialized.
        """
        for key, value in values.items():
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Invalid value for {key}: {value}. Must be numeric."
                )

        return cls(
            shooting=Shooting(score=values.get("shooting", 65)),
            dribbling=Dribbling(score=values.get("dribbling", 65)),
            passing=Passing(score=values.get("passing", 65)),
            tackling=Tackling(score=values.get("tackling", 65)),
            fitness=Fitness(score=values.get("fitness", 65)),
            goalkeeping=Goalkeeping(score=values.get("goalkeeping", 65)),
        )


@dataclass
class Player:
    """
    Represents a player with a name, attributes, and form.

    :param name:
        The player's name.
    :param attributes:
        An instance of the `Attributes` class representing the player's
        skill attributes.
    :param form:
        A multiplier that adjusts the player's overall rating based on
        current form.

    Methods:
        - get_overall_rating():
            Calculates the player's overall rating based on attributes
            and form using TrueSkill.
    """

    name: str
    attributes: Attributes
    form: int

    def get_overall_rating(self) -> float:
        """
        Get the player's overall rating, considering their form and attributes.
        This uses TrueSkill to calculate the rating based on the player's
        attributes and form.

        :return:
            A float representing the player's overall rating, adjusted by their
            form (e.g., if form is positive, it boosts the rating).
        """
        total_rating = sum(
            getattr(self.attributes, attribute).score
            for attribute in self.attributes.__dict__.keys()
        )
        # Calculate TrueSkill rating based on form and attributes
        true_skill_rating = trueskill.Rating(mu=total_rating / 6, sigma=8.333)
        return true_skill_rating.mu * (1 + 0.1 * self.form)


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
