"""Button entities for Narwal robot vacuum."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NarwalConfigEntry
from .coordinator import NarwalCoordinator
from .entity import NarwalEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NarwalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Narwal button entities."""
    coordinator = entry.runtime_data
    async_add_entities([
        NarwalLocateButton(coordinator),
        NarwalWakeButton(coordinator),
        NarwalDockButton(coordinator, "empty_dustbin", "mdi:delete-empty", "empty_dustbin"),
        NarwalDockButton(coordinator, "wash_mop", "mdi:water-sync", "wash_mop"),
        NarwalDockButton(coordinator, "dry_mop", "mdi:weather-windy", "dry_mop"),
    ])


class NarwalLocateButton(NarwalEntity, ButtonEntity):
    """Makes the vacuum beep so you can find it."""

    _attr_translation_key = "locate"
    _attr_icon = "mdi:map-marker-question"

    def __init__(self, coordinator: NarwalCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.config_entry.data['device_name']}_locate"
        )

    async def async_press(self) -> None:
        """Send the yell/locate command to the vacuum."""
        resp = await self.coordinator.client.locate()
        if not resp.success:
            _LOGGER.warning("Locate returned code=%s", resp.result_code)


class NarwalWakeButton(NarwalEntity, ButtonEntity):
    """Wake the vacuum from sleep by sending an active_robot notification."""

    _attr_translation_key = "wake"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator: NarwalCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.config_entry.data['device_name']}_wake"
        )

    async def async_press(self) -> None:
        """Send active_robot_publish to wake the vacuum."""
        await self.coordinator.client.notify_active()
        _LOGGER.info("Sent wake (active_robot) notification")


class NarwalDockButton(NarwalEntity, ButtonEntity):
    """Runs a base-station job: empty dustbin, wash mops or dry mops."""

    def __init__(
        self, coordinator: NarwalCoordinator, key: str, icon: str, method: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_translation_key = key
        self._attr_icon = icon
        self._method = method
        self._attr_unique_id = (
            f"{coordinator.config_entry.data['device_name']}_{key}"
        )

    async def async_press(self) -> None:
        """Send the dock command; surface a refusal in the UI."""
        client = self.coordinator.client
        await client.notify_active()
        resp = await getattr(client, self._method)()
        _LOGGER.info("%s returned code=%s", self._method, resp.result_code)
        if not resp.success:
            raise HomeAssistantError(
                f"The vacuum declined {self._method.replace('_', ' ')} "
                f"(code {resp.result_code}). It usually needs to be on the dock."
            )
