/**
 * Ingredient quantity parsing and scaling.
 *
 * Handles: integers, decimals, plain fractions (1/4), mixed numbers (1 1/2),
 * and common Unicode vulgar fractions (½ ⅓ ¼ …).
 *
 * Quantities that can't be parsed are returned unchanged so "a pinch of salt"
 * or "to taste" are never corrupted.
 */

// Unicode vulgar fraction → decimal
const UNICODE_FRACTIONS: Record<string, number> = {
  '½': 0.5,
  '⅓': 1 / 3,
  '⅔': 2 / 3,
  '¼': 0.25,
  '¾': 0.75,
  '⅕': 0.2,
  '⅖': 0.4,
  '⅗': 0.6,
  '⅘': 0.8,
  '⅙': 1 / 6,
  '⅚': 5 / 6,
  '⅛': 0.125,
  '⅜': 0.375,
  '⅝': 0.625,
  '⅞': 0.875,
}

// Matches the leading quantity portion of an ingredient string.
// Groups: (integer_part) (fraction_numerator) (fraction_denominator) (unicode_fraction)
// Examples:
//   "1 1/2 cups"  → integer=1, num=1, den=2
//   "3/4 cup"     → integer=undefined, num=3, den=4
//   "2 eggs"      → integer=2
//   "½ tsp"       → unicode=½
const QTY_RE =
  /^(\d+(?:\.\d+)?)?(?:\s*(\d+)\s*\/\s*(\d+))?([½⅓⅔¼¾⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞])?/

interface ParsedQty {
  value: number
  /** length of the matched prefix in the original string */
  length: number
}

function parseLeadingQty(ingredient: string): ParsedQty | null {
  const m = QTY_RE.exec(ingredient)
  if (!m) return null

  const intPart = m[1] ? parseFloat(m[1]) : undefined
  const num = m[2] ? parseInt(m[2], 10) : undefined
  const den = m[3] ? parseInt(m[3], 10) : undefined
  const uni = m[4] ? UNICODE_FRACTIONS[m[4]] : undefined

  let value: number | undefined

  if (intPart !== undefined && num !== undefined && den !== undefined) {
    // Mixed number: "1 1/2"
    value = intPart + num / den
  } else if (num !== undefined && den !== undefined) {
    // Plain fraction: "3/4"
    value = num / den
  } else if (intPart !== undefined) {
    value = intPart
  } else if (uni !== undefined) {
    value = uni
  }

  if (value === undefined || value === 0) return null

  return { value, length: m[0].length }
}

// Nice fraction representations for common values
const FRACTION_MAP: Array<[number, string]> = [
  [1 / 8, '1/8'],
  [1 / 4, '1/4'],
  [1 / 3, '1/3'],
  [3 / 8, '3/8'],
  [1 / 2, '1/2'],
  [5 / 8, '5/8'],
  [2 / 3, '2/3'],
  [3 / 4, '3/4'],
  [7 / 8, '7/8'],
]

function formatQty(value: number): string {
  if (value <= 0) return ''

  const whole = Math.floor(value)
  const frac = value - whole

  // Check if the fractional part snaps to a common fraction (within 1%)
  const TOLERANCE = 0.013
  const matched = FRACTION_MAP.find(([v]) => Math.abs(frac - v) < TOLERANCE)
  const fracStr = matched ? matched[1] : null

  if (whole === 0 && fracStr) return fracStr
  if (whole > 0 && fracStr) return `${whole} ${fracStr}`
  if (whole > 0 && frac < TOLERANCE) return `${whole}`

  // Fall back to a clean decimal
  // Use 2 sig figs for small numbers, 1 decimal for larger
  if (value < 1) return value.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
  return parseFloat(value.toFixed(1)).toString()
}

/**
 * Extract the base serving count from a servings string like "4 servings",
 * "Serves 6", "Makes 12 cookies". Returns null if none found.
 */
export function parseServingCount(servings: string | null | undefined): number | null {
  if (!servings) return null
  const m = servings.match(/\d+/)
  return m ? parseInt(m[0], 10) : null
}

/**
 * Scale a single ingredient string by the ratio (targetServings / baseServings).
 * If the ingredient has no parseable leading quantity, it is returned unchanged.
 */
export function scaleIngredient(ingredient: string, ratio: number): string {
  if (ratio === 1) return ingredient

  const parsed = parseLeadingQty(ingredient.trimStart())
  if (!parsed) return ingredient

  const scaled = parsed.value * ratio
  const formatted = formatQty(scaled)
  if (!formatted) return ingredient

  const rest = ingredient.slice(parsed.length)
  return formatted + rest
}
