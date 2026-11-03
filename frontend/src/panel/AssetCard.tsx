import type { components } from "../api/schema.gen";
import { formatPrice, formatRadius } from "../i18n/format";
import { es } from "../i18n/es";
import { categoryImage } from "./categoryImage";

type PublicAsset = components["schemas"]["PublicAsset"];

// El texto del anuncio es de un tercero: entra siempre como texto de React, nunca como HTML
export function AssetCard({ asset }: { asset: PublicAsset }) {
  const price = formatPrice(asset.price, asset.price_unit);
  return (
    <li className="flex gap-3 border-b border-ink/10 py-3 last:border-b-0">
      <img
        src={categoryImage(asset.category_slug)}
        alt=""
        width={72}
        height={72}
        loading="lazy"
        decoding="async"
        className="size-18 shrink-0 rounded-xl object-cover"
      />
      <div className="grid min-w-0 content-center gap-0.5">
        <p className="line-clamp-2 leading-tight font-semibold wrap-anywhere">
          <bdi>{asset.title}</bdi>
        </p>
        <p className="text-sm text-muted wrap-anywhere">{asset.category_name}</p>
        <p className="flex items-center gap-1.5 text-sm text-muted">
          <svg
            aria-hidden="true"
            viewBox="0 0 16 16"
            className="size-4 shrink-0"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeDasharray="2.5 2"
          >
            <circle cx="8" cy="8" r="6.5" />
          </svg>
          {es.panel.radius.replace("{radius}", formatRadius(asset.privacy_radius))}
        </p>
        <p className="tabular-nums">
          <span className="font-bold text-accent">{price.amount}</span>&nbsp;/ {price.unit}
        </p>
      </div>
    </li>
  );
}
