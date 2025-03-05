"""
This module defines the Player and Attributes classes for managing player 
info, including their attributes such as shooting, dribbling, passing, tackling, 
fitness, and goalkeeping. Each attribute is stored as a raw value, and the 
overall rating of the player is calculated using TrueSkill, which dynamically 
adjusts based on form.

"""

from dataclasses import dataclass

import trueskill

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
        """
        Get the score of the attribute.

        :return:
            The score of the attribute.
        """
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

    :param name:
        The player's name.
    :param attributes:
        An instance of the `Attributes` class representing the player's
        skill attributes.
    :param form:
        A multiplier that adjusts the player's overall rating based on
        current form.
        This ranges from 0 to 10, where the former is no form and 10 is super
        hot fire form.

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
            getattr(self.attributes, attribute).get_score()
            for attribute in vars(self.attributes)
        )

        # Normalize rating to a mean value
        true_skill_rating = trueskill.Rating(mu=total_rating / 6, sigma=8.333)

        # Adjust based on form
        return true_skill_rating.mu * (1 + 0.05 * self.form)
