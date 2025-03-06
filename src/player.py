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
    Represents a player with a name, attributes, form, and TrueSkill rating.

    :param name: Player's name.
    :param attributes: An instance of `Attributes` containing player stats.
    :param form: Represents current player form (affects rating).
    """

    name: str
    attributes: Attributes
    form: int  # 0-10, affecting performance

    min_sigma: float = 1.0  # Ensure sigma never drops to 0
    mu: float = 5.0

    def __post_init__(self):
        """Ensures valid form range and initializes TrueSkill rating."""
        # Clamp the form between 0 and 10
        self.form = max(0, min(self.form, 10))

        # Initialize TrueSkill rating based on base player rating
        self.mu = self._get_base_rating()
        self._calculate_trueskill()

    def _calculate_trueskill(self):
        """
        Calculate the TrueSkill.
        """
        self.trueskill_rating = trueskill.Rating(
            mu=self.mu,
            sigma=max(10 - self.form, self.min_sigma),
        )

    def _get_base_rating(self) -> float:
        """
        Compute base rating as the mean of attributes.

        :return:
            The player's base skill rating.
        """
        total_rating = sum(
            getattr(self.attributes, attr).get_score()
            for attr in vars(self.attributes)
        )
        return total_rating / NUM_ATTRIBUTES  # Normalize the rating

    def update_trueskill(self, won: bool):
        """
        Updates the player's TrueSkill rating and form after a match.

        :param won: True if the player won, False otherwise.
        """
        # Form should remain between 0-10
        if won:
            self.form = min(self.form + 1, 10)
        else:
            self.form = max(self.form - 1, 0)

        # Dynamic adjustment
        adjustment_factor = 1 + 0.1 * self.form if won else 0.9

        # Clamp the TrueSkill value within realistic limits
        self.mu = min(max(self.trueskill_rating.mu * adjustment_factor, 1), 10)

        self.trueskill_rating = trueskill.Rating(
            mu=self.mu, sigma=max(10 - self.form, self.min_sigma)
        )

    def get_overall_rating(self) -> float:
        """
        Get the overall rating of the player, taking form into account.
        """
        self._calculate_trueskill()
        return self.trueskill_rating.mu * (1 + 0.05 * self.form)
