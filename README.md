# Auckland Bin Collection

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![GitHub release](https://img.shields.io/github/v/release/fishy242/auckland_bin_collection)](https://github.com/fishy242/auckland_bin_collection/releases)
[![GitHub license](https://img.shields.io/github/license/fishy242/auckland_bin_collection)](LICENSE)

Home Assistant custom integration for Auckland Council rubbish, recycling, and food scraps collection dates.

## Features

- UI configuration flow.
- Native calendar entity for collection reminders and automations.
- Sensor entities for dashboard display.
- Separate calendar events for each bin type on the same day.
- Food scraps are ordered last so rubbish and recycling stay visible first in compact calendar cards.
- Fetching is scheduled around current collection data instead of polling every day.

## Installation

### HACS

1. Open HACS in Home Assistant.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add this repository URL:

   ```text
   https://github.com/fishy242/auckland_bin_collection
   ```

4. Select **Integration** as the category.
5. Install **Auckland Bin Collection**.
6. Restart Home Assistant.

### Manual

Copy `custom_components/auckland_bin_collection` from this repository into:

```text
<config>/custom_components/auckland_bin_collection
```

Restart Home Assistant after copying the files.

## Configuration

1. In Home Assistant, go to **Settings** > **Devices & services**.
2. Select **Add integration**.
3. Search for **Auckland Bin Collection**.
4. Enter your Auckland Council location ID.

### Location ID

Open the [Auckland Council collection day page](https://www.aucklandcouncil.govt.nz/rubbish-recycling/rubbish-recycling-collections/Pages/rubbish-recycling-collection-days.aspx), search for your address, then use the 11-digit ID from the result page URL.

Example URL:

```text
https://www.aucklandcouncil.govt.nz/en/rubbish-recycling/rubbish-recycling-collections/rubbish-recycling-collection-days/12345678901.html
```

In this example, the location ID is `12345678901`.

## Entities

| Entity | Description |
| --- | --- |
| `calendar.auckland_bin_collection` | Calendar events for upcoming collections. |
| `sensor.auckland_bin_collection_upcoming` | Date and attributes for the next collection day. |
| `sensor.auckland_bin_collection_next` | Date and attributes for the following collection day. |

### Calendar

The calendar entity returns separate all-day events for each bin type. If rubbish, recycling, and food scraps are collected on the same day, `calendar.get_events` returns three events.

The calendar entity's current `message` attribute summarizes all bin types on the next collection day, for example:

```text
Rubbish, Recycling, Food scraps
```

### Sensor Attributes

| Attribute | Description |
| --- | --- |
| `location_id` | Auckland Council location ID. |
| `date` | Collection date text from Auckland Council. |
| `rubbish` | `true` when rubbish is collected on this date. |
| `recycle` | `true` when recycling is collected on this date. |
| `food scraps` | `true` when food scraps are collected on this date. |
| `query_url` | Auckland Council page used for the location. |
| `last_updated` | Last successful fetch timestamp. |

## Fetch Behaviour

The integration fetches data when Home Assistant starts, then schedules future successful refreshes after the current collection data expires.

For example, if the next collection event is on `2026-06-29` and ends at `2026-06-30 00:00:00`, the next scheduled fetch starts on `2026-06-30`.

Successful refreshes are randomized around noon with a four-hour jitter, so the target window is roughly `08:00` to `16:00` local time. Failed fetches retry after a randomized `2` to `6` hour delay and continue retrying until a fetch succeeds.

## Automation Example

Use `calendar.get_events` when you want a single daily notification with every bin type collected that day:

```yaml
alias: Daily Bin Reminder
mode: single
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: calendar.get_events
    target:
      entity_id: calendar.auckland_bin_collection
    data:
      duration:
        hours: 24
    response_variable: scheduled_bins

  - condition: template
    value_template: "{{ scheduled_bins['calendar.auckland_bin_collection']['events'] | length > 0 }}"

  - service: notify.notify
    data:
      message: >
        Take out the bins today:
        {% for event in scheduled_bins['calendar.auckland_bin_collection']['events'] %}
          - {{ event.summary }}
        {% endfor %}
```

## Dashboard Example

Add a Markdown card using the state sensors:

```text
Upcoming: **{{ state_attr('sensor.auckland_bin_collection_upcoming', 'date') }}**{% if state_attr('sensor.auckland_bin_collection_upcoming', 'rubbish') == 'true' %} <ha-icon icon="mdi:trash-can-outline"></ha-icon>{% endif %}{% if state_attr('sensor.auckland_bin_collection_upcoming', 'recycle') == 'true' %} <ha-icon icon="mdi:recycle"></ha-icon>{% endif %}{% if state_attr('sensor.auckland_bin_collection_upcoming', 'food scraps') == 'true' %} <ha-icon icon="mdi:compost"></ha-icon>{% endif %}

Next: **{{ state_attr('sensor.auckland_bin_collection_next', 'date') }}**{% if state_attr('sensor.auckland_bin_collection_next', 'rubbish') == 'true' %} <ha-icon icon="mdi:trash-can-outline"></ha-icon>{% endif %}{% if state_attr('sensor.auckland_bin_collection_next', 'recycle') == 'true' %} <ha-icon icon="mdi:recycle"></ha-icon>{% endif %}{% if state_attr('sensor.auckland_bin_collection_next', 'food scraps') == 'true' %} <ha-icon icon="mdi:compost"></ha-icon>{% endif %}
```

![Markdown card example](img/abc_markdown_card.png)

## Changelog

| Version | Notes |
| --- | --- |
| 0.4.0 | Schedule fetches after current collection data expires; add randomized daytime refreshes and 2-6 hour retries; summarize all next-day bin types in the calendar entity message. |
| 0.3.1 | Always list food scraps last so rubbish and recycling stay visible first. |
| 0.3.0 | Added native calendar entity and optimized polling frequency. |
| 0.2.0 | Updated parser for Auckland Council food scraps collection data. |
| 0.1.0 | Initial release. |
