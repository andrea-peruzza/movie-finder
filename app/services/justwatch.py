import httpx
import asyncio
from typing import Dict, Any, Optional, List

GQL_URL = "https://apis.justwatch.com/graphql"
IMAGE_BASE_URL = "https://images.justwatch.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Content-Type": "application/json"
}

SEARCH_QUERY = """
query GetSearchTitles($country: Country!, $language: Language!, $searchTitlesFilter: TitleFilter) {
  popularTitles(country: $country, filter: $searchTitlesFilter) {
    edges {
      node {
        id
        objectId
        objectType
        content(country: $country, language: $language) {
          title
          originalReleaseYear
          posterUrl
          shortDescription
          scoring {
            imdbScore
            tmdbScore
          }
          genres {
            shortName
            translation(language: $language)
          }
        }
        offers(country: $country, platform: WEB) {
          monetizationType
          presentationType
          package {
            id
            packageId
            clearName
            shortName
            icon
          }
          standardWebURL
        }
      }
    }
  }
}
"""

def format_image_url(template_url: Optional[str], size: str = "s332", ext: str = "webp") -> Optional[str]:
    if not template_url:
        return None
    # Template is like: /poster/112379151/{profile}/inception.{format}
    # or /icon/322992749/{profile}/amazonprimevideo.{format}
    url = template_url.replace("{profile}", size).replace("{format}", ext)
    if not url.startswith("http"):
        url = IMAGE_BASE_URL + url
    return url

async def search_justwatch(
    title: str,
    release_year: Optional[int] = None,
    client: Optional[httpx.AsyncClient] = None
) -> Optional[Dict[str, Any]]:
    """
    Search JustWatch in Italy for a movie by title and year.
    Returns matched details, content info, and all offers.
    """
    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=12.0)
        close_client = True

    variables = {
        "country": "IT",
        "language": "it",
        "searchTitlesFilter": {
            "searchQuery": title
        }
    }

    try:
        response = await client.post(
            GQL_URL,
            json={"query": SEARCH_QUERY, "variables": variables},
            headers=HEADERS
        )
        if response.status_code != 200:
            return None

        data = response.json()
        edges = data.get("data", {}).get("popularTitles", {}).get("edges", [])
        if not edges:
            return None

        # Best match scoring
        best_node = None
        for edge in edges:
            node = edge["node"]
            c = node.get("content") or {}
            node_year = c.get("originalReleaseYear")

            # Match movie content types
            if release_year and node_year:
                if abs(node_year - release_year) <= 1:
                    best_node = node
                    break
        
        if not best_node:
            best_node = edges[0]["node"]

        content = best_node.get("content") or {}
        raw_offers = best_node.get("offers") or []

        # Parse genres
        genres = []
        for g in content.get("genres") or []:
            if g:
                genre_name = g.get("translation") or g.get("shortName")
                if genre_name and genre_name not in genres:
                    genres.append(genre_name)

        # Parse scoring
        scoring = content.get("scoring") or {}
        imdb_score = scoring.get("imdbScore")

        # Parse poster
        raw_poster = content.get("posterUrl")
        poster_url = format_image_url(raw_poster, size="s332")

        # Parse offers
        parsed_offers = []
        seen_offers = set()
        for off in raw_offers:
            pkg = off.get("package") or {}
            clear_name = pkg.get("clearName")
            m_type = off.get("monetizationType")
            web_url = off.get("standardWebURL")
            if not clear_name or not m_type:
                continue

            # Deduplicate by provider name + monetization type
            offer_key = (clear_name.lower(), m_type)
            if offer_key in seen_offers:
                continue
            seen_offers.add(offer_key)

            icon_url = format_image_url(pkg.get("icon"), size="s100", ext="webp")

            parsed_offers.append({
                "provider_name": clear_name,
                "provider_short_name": pkg.get("shortName"),
                "provider_id": pkg.get("packageId") or pkg.get("id"),
                "provider_icon": icon_url,
                "monetization_type": m_type,
                "web_url": web_url,
                "presentation_type": off.get("presentation_type") or "HD"
            })

        return {
            "jw_id": str(best_node.get("id")),
            "jw_title": content.get("title"),
            "jw_year": content.get("originalReleaseYear"),
            "poster_url": poster_url,
            "imdb_score": imdb_score,
            "genres": genres,
            "overview": content.get("shortDescription"),
            "offers": parsed_offers
        }

    except Exception as e:
        print(f"Error querying JustWatch for '{title}': {e}")
        return None
    finally:
        if close_client:
            await client.aclose()
