"""
This module defines the `Player` and `Attributes` classes for managing player information,
including their attributes such as shooting, dribbling, passing, tackling, fitness, and goalkeeping.
Each attribute is stored as a `trueskill.Rating` object, and the overall rating of the player is
calculated based on these attributes and their form.

Classes:
    - Shooting: Represents a player's shooting ability.
    - Dribbling: Represents a player's dribbling ability.
    - Passing: Represents a player's passing ability.
    - Tackling: Represents a player's tackling ability.
    - Fitness: Represents a player's fitness.
    - Goalkeeping: Represents a player's goalkeeping ability.
    - Attributes: Groups all player attributes into a single dataclass.
    - Player: Represents a player with a name, attributes, and form. Provides a method to calculate
              the player's overall rating.
"""

from dataclasses import dataclass

import trueskill


@dataclass
class Shooting:
    """
    Represents a player's shooting ability.

    :mu: The skill rating (mean).
    :sigma: The uncertainty of the rating.
    """

    mu: float
    sigma: float


@dataclass
class Dribbling:
    """
    Represents a player's dribbling ability.

    :mu: The skill rating (mean).
    :sigma: The uncertainty of the rating.
    """

    mu: float
    sigma: float


@dataclass
class Passing:
    """
    Represents a player's passing ability.

    :mu: The skill rating (mean).
    :sigma: The uncertainty of the rating.
    """

    mu: float
    sigma: float


@dataclass
class Tackling:
    """
    Represents a player's tackling ability.

    :mu: The skill rating (mean).
    :sigma: The uncertainty of the rating.
    """

    mu: float
    sigma: float


@dataclass
class Fitness:
    """
    Represents a player's fitness level.

    :mu: The skill rating (mean).
    :sigma: The uncertainty of the rating.
    """

    mu: float
    sigma: float


@dataclass
class Goalkeeping:
    """
    Represents a player's goalkeeping ability.

    :mu: The skill rating (mean).
    :sigma: The uncertainty of the rating.
    """

    mu: float
    sigma: float


@dataclass
class Attributes:
    """
    Groups all of a player's attributes into a single dataclass.

    :shooting: A player's shooting ability.
    :dribbling: A player's dribbling ability.
    :passing: A player's passing ability.
    :tackling: A player's tackling ability.
    :fitness: A player's fitness.
    :goalkeeping: A player's goalkeeping ability.
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

        :param values: A dictionary containing player attribute values.
                       The dictionary should contain keys for each attribute:
                       'shooting', 'dribbling', 'passing', 'tackling', 'fitness', and 'goalkeeping'.
                       Each key should have a 'mu' and 'sigma' value for the rating.

        :return: An `Attributes` object with all attributes initialized.
        """
        return cls(
            shooting=Shooting(
                mu=values.get("shooting", 25),
                sigma=values.get("shooting_sigma", 8.333),
            ),
            dribbling=Dribbling(
                mu=values.get("dribbling", 25),
                sigma=values.get("dribbling_sigma", 8.333),
            ),
            passing=Passing(
                mu=values.get("passing", 25),
                sigma=values.get("passing_sigma", 8.333),
            ),
            tackling=Tackling(
                mu=values.get("tackling", 25),
                sigma=values.get("tackling_sigma", 8.333),
            ),
            fitness=Fitness(
                mu=values.get("fitness", 25),
                sigma=values.get("fitness_sigma", 8.333),
            ),
            goalkeeping=Goalkeeping(
                mu=values.get("goalkeeping", 25),
                sigma=values.get("goalkeeping_sigma", 8.333),
            ),
        )


@dataclass
class Player:
    """
    Represents a player with a name, attributes, and form.

    :name: The player's name.
    :attributes: An instance of the `Attributes` class representing the player's skill attributes.
    :form: A multiplier that adjusts the player's overall rating based on current form.

    Methods:
        - get_overall_rating(): Calculates the player's overall rating based on attributes and form.
    """

    name: str
    attributes: Attributes
    form: int

    def get_overall_rating(self) -> float:
        """
        Get the player's overall rating, considering their form and attributes.

        :return: A float representing the player's overall rating, adjusted by their form.
        """
        total_rating = sum(
            getattr(self.attributes, attribute).mu
            for attribute in self.attributes.__dict__.keys()
        )
        # Apply the form factor to the overall rating
        return (total_rating / len(self.attributes.__dict__.keys())) * (
            1 + 0.1 * self.form
        )  # Adjust the form factor as needed


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
