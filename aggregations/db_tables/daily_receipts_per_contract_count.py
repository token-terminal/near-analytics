import datetime

from . import DAY_LEN_SECONDS, daily_start_of_range
from ..periodic_aggregations import PeriodicAggregations


class DailyReceiptsPerContractCount(PeriodicAggregations):
    @property
    def sql_create_table(self):
        # Suppose we have at most 10^5 (100K) transactions per second.
        # In the worst case, they are all from one account.
        # It gives ~10^10 transactions per day.
        # It means we fit into BIGINT (10^18)
        return '''
            CREATE TABLE IF NOT EXISTS daily_receipts_per_contract_count
            (
                collected_for_day DATE NOT NULL,
                contract_id       TEXT NOT NULL,
                receipts_count    BIGINT NOT NULL,
                CONSTRAINT daily_receipts_per_contract_count_pk PRIMARY KEY (collected_for_day, contract_id)
            );
            CREATE INDEX IF NOT EXISTS daily_receipts_per_contract_count_idx
                ON daily_receipts_per_contract_count (collected_for_day, receipts_count DESC)
        '''

    @property
    def sql_drop_table(self):
        return '''
            DROP TABLE IF EXISTS daily_receipts_per_contract_count
        '''

    @property
    def sql_select(self):
        return '''
            SELECT
                action_receipt_actions.receipt_receiver_account_id,
                COUNT(action_receipt_actions.receipt_id) AS receipts_count
            FROM action_receipt_actions
            WHERE action_receipt_actions.action_kind = 'FUNCTION_CALL'
                AND action_receipt_actions.receipt_included_in_block_timestamp >= %(from_timestamp)s
                AND action_receipt_actions.receipt_included_in_block_timestamp < %(to_timestamp)s
            GROUP BY action_receipt_actions.receipt_receiver_account_id
        '''

    @property
    def sql_insert(self):
        return '''
            INSERT INTO daily_receipts_per_contract_count VALUES %s
            ON CONFLICT DO NOTHING
        '''

    @property
    def duration_seconds(self):
        return DAY_LEN_SECONDS

    def start_of_range(self, timestamp: int) -> int:
        return daily_start_of_range(timestamp)

    @staticmethod
    def prepare_data(parameters: list, **kwargs) -> list:
        computed_for = datetime.datetime.utcfromtimestamp(kwargs['start_of_range']).strftime('%Y-%m-%d')
        return [(computed_for, contract_id, count) for (contract_id, count) in parameters]
