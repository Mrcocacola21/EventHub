export function getListFromResponse(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.results)) {
    return data.results;
  }

  return [];
}

export function normalizeListResponse(data) {
  return getListFromResponse(data);
}

export function normalizePaginatedResponse(data) {
  const items = getListFromResponse(data);
  const isPaginated =
    Boolean(data) && !Array.isArray(data) && Array.isArray(data.results);

  return {
    items,
    results: items,
    count: typeof data?.count === "number" ? data.count : items.length,
    next: data?.next || null,
    previous: data?.previous || null,
    isPaginated,
  };
}

export function groupMatchesByRound(data) {
  if (!data) {
    return [];
  }

  if (Array.isArray(data.rounds)) {
    return data.rounds.map((round) => ({
      round: round.round,
      matches: getListFromResponse(round.matches),
    }));
  }

  const matches = getListFromResponse(data);
  const grouped = matches.reduce((accumulator, match) => {
    const roundNumber = match.round || 1;

    if (!accumulator.has(roundNumber)) {
      accumulator.set(roundNumber, []);
    }

    accumulator.get(roundNumber).push(match);
    return accumulator;
  }, new Map());

  return Array.from(grouped.entries())
    .sort(([roundA], [roundB]) => Number(roundA) - Number(roundB))
    .map(([round, roundMatches]) => ({
      round,
      matches: roundMatches.sort(
        (matchA, matchB) => Number(matchA.position) - Number(matchB.position),
      ),
    }));
}
