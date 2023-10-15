from dadata import Dadata
from pydantic import BaseModel
from typing import Any


class DadataAddress(BaseModel):
    source: str | None
    result: str | None
    postal_code: str | None
    country: str | None
    country_iso_code: str | None
    federal_district: str | None
    region_fias_id: str | None
    region_kladr_id: str | None
    region_iso_code: str | None
    region_with_type: str | None
    region_type: str | None
    region_type_full: str | None
    region: str | None
    area_fias_id: str | None
    area_kladr_id: str | None
    area_with_type: str | None
    area_type: str | None
    area_type_full: str | None
    area: str | None
    city_fias_id: str | None
    city_kladr_id: str | None
    city_with_type: str | None
    city_type: str | None
    city_type_full: str | None
    city: str | None
    city_area: str | None
    city_district_fias_id: str | None
    city_district_kladr_id: str | None
    city_district_with_type: str | None
    city_district_type: str | None
    city_district_type_full: str | None
    city_district: str | None
    settlement_fias_id: str | None
    settlement_kladr_id: str | None
    settlement_with_type: str | None
    settlement_type: str | None
    settlement_type_full: str | None
    settlement: str | None
    street_fias_id: str | None
    street_kladr_id: str | None
    street_with_type: str | None
    street_type: str | None
    street_type_full: str | None
    street: str | None
    stead_fias_id: str | None
    stead_kladr_id: str | None
    stead_cadnum: str | None
    stead_type: str | None
    stead_type_full: str | None
    stead: str | None
    house_fias_id: str | None
    house_kladr_id: str | None
    house_cadnum: str | None
    house_type: str | None
    house_type_full: str | None
    house: str | None
    block_type: str | None
    block_type_full: str | None
    block: str | None
    entrance: str | None
    floor: str | None
    flat_fias_id: str | None
    flat_cadnum: str | None
    flat_type: str | None
    flat_type_full: str | None
    flat: str | None
    flat_area: str | None
    square_meter_price: str | None
    flat_price: str | None
    postal_box: str | None
    fias_id: str | None
    fias_code: str | None
    fias_level: str | None
    fias_actuality_state: str | None
    kladr_id: str | None
    capital_marker: str | None
    okato: str | None
    oktmo: str | None
    tax_office: str | None
    tax_office_legal: str | None
    timezone: str | None
    geo_lat: str | None
    geo_lon: str | None
    beltway_hit: str | None
    beltway_distance: str | None
    qc_geo: int | None
    qc_complete: int | None
    qc_house: int | None
    qc: int | None
    unparsed_parts: str | None
    metro: list[dict[str, Any]] | None


class DadataRepository:
    def __init__(self, token, secret):
        self.dadata = Dadata(token, secret)

    def get_clean_data(self, address: str) -> DadataAddress:
        response = self.dadata.clean("address", address)
        return DadataAddress(**response)


if __name__ == '__main__':
    from dotenv import load_dotenv
    import os
    load_dotenv()
    dadata = DadataRepository(os.environ.get('dadata_token'), os.environ.get('dadata_secret'))
    address = dadata.get_clean_data('Санкт-Петербург, Суворовский пр-т, 43-45Б, 25')
    print(address.flat_area)
    print(address.flat_cadnum)
    print(address.house_cadnum)
else:
    from bot.config import config
    dadata = DadataRepository(config.dadata_token.get_secret_value(), config.dadata_secret.get_secret_value())
