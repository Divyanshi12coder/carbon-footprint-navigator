/**
 * Central image registry. Every photo is openly licensed (Wikimedia Commons), stored locally as
 * optimised WebP in /public/images, and credited on the Methodology page. To replace an image,
 * drop a new file in public/images and update its entry here — nothing else references paths.
 */

export interface SiteImage {
  src: string
  alt: string
  credit: { author: string; license: string; licenseUrl: string; source: string }
}

const commons = (file: string) => `https://commons.wikimedia.org/wiki/File:${file}`

export const images = {
  heroCity: {
    src: '/images/hero-gardens.webp',
    alt: 'Aerial view of the Supertree Grove vertical gardens surrounded by dense greenery in Singapore',
    credit: {
      author: 'Mustang Joe',
      license: 'CC0',
      licenseUrl: 'https://creativecommons.org/publicdomain/zero/1.0/',
      source: commons('Supertree_Grove,_Gardens_by_the_Bay,_Singapore1.jpg'),
    },
  },
  forest: {
    src: '/images/forest-roruper.webp',
    alt: 'Sunlight streaming through a green beech forest',
    credit: {
      author: 'Dietmar Rabich',
      license: 'CC BY-SA 4.0',
      licenseUrl: 'https://creativecommons.org/licenses/by-sa/4.0',
      source: commons('Dülmen,_Rorup,_NSG_Roruper_Holz_--_2021_--_8187-91.jpg'),
    },
  },
  evCharging: {
    src: '/images/ev-stuttgart.webp',
    alt: 'A small electric car plugged into a public charging station',
    credit: {
      author: 'Julian Herzog',
      license: 'CC BY 4.0',
      licenseUrl: 'https://creativecommons.org/licenses/by/4.0',
      source: commons('Car2Go_Charging_Station_Stuttgart_2013_01.jpg'),
    },
  },
  tram: {
    src: '/images/tram-prague.webp',
    alt: 'A modern tram at a stop in the evening',
    credit: {
      author: 'Honza Groh (Jagro)',
      license: 'CC BY-SA 3.0',
      licenseUrl: 'https://creativecommons.org/licenses/by-sa/3.0',
      source: commons('Škoda_15T,_smyčka_Radlická.jpg'),
    },
  },
  solar: {
    src: '/images/solar-roof-nieder-olm.webp',
    alt: 'Aerial view of farmland with solar panels covering a large barn roof',
    credit: {
      author: 'Matti Blume',
      license: 'CC BY-SA 4.0',
      licenseUrl: 'https://creativecommons.org/licenses/by-sa/4.0',
      source: commons('Solar_power,_Nieder-Olm_(P1090617).jpg'),
    },
  },
  wind: {
    src: '/images/wind-sussex.webp',
    alt: 'Wind turbines and power lines across green fields under a blue sky',
    credit: {
      author: 'Diliff',
      license: 'CC BY-SA 3.0',
      licenseUrl: 'https://creativecommons.org/licenses/by-sa/3.0',
      source: commons('Wind_Turbines_and_Power_Lines,_East_Sussex,_England_-_April_2009.jpg'),
    },
  },
  cycling: {
    src: '/images/cycling-commute.webp',
    alt: 'A commuter cycling through an underpass, framed by a round opening',
    credit: {
      author: 'Petar Milošević',
      license: 'CC BY-SA 4.0',
      licenseUrl: 'https://creativecommons.org/licenses/by-sa/4.0',
      source: commons('Commuting_by_bicycle.jpg'),
    },
  },
  recycling: {
    src: '/images/recycling-drammen.webp',
    alt: 'A row of public recycling collection points beside a street',
    credit: {
      author: 'Peulle',
      license: 'CC0',
      licenseUrl: 'https://creativecommons.org/publicdomain/zero/1.0/',
      source: commons('Recycling_bins_Drammen.jpg'),
    },
  },
  food: {
    src: '/images/food-romanesco.webp',
    alt: 'Two heads of romanesco broccoli on a soft green background',
    credit: {
      author: 'George Chernilevsky',
      license: 'CC BY 4.0',
      licenseUrl: 'https://creativecommons.org/licenses/by/4.0',
      source: commons('Romanesco_broccoli_2025_G2.jpg'),
    },
  },
  earth: {
    src: '/images/earth-apollo17.webp',
    alt: 'The Earth photographed from Apollo 17',
    credit: {
      author: 'NASA / Apollo 17 crew',
      license: 'Public domain',
      licenseUrl: 'https://www.nasa.gov/nasa-brand-center/images-and-media/',
      source: commons('The_Earth_seen_from_Apollo_17.jpg'),
    },
  },
} satisfies Record<string, SiteImage>

export type ImageKey = keyof typeof images
