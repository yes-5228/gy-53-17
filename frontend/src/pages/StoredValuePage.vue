<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { parkingApi } from "../api/parking";

const transactions = ref([]);
const cards = ref([]);
const filterForm = reactive({
  plate_number: "",
  type: "",
});

async function loadData() {
  const [txData, cardData] = await Promise.all([
    parkingApi.getTransactions(filterForm.plate_number || undefined),
    parkingApi.getCards(),
  ]);
  transactions.value = txData.items;
  cards.value = cardData.items;
}

const filteredTransactions = computed(() => {
  let items = transactions.value;
  if (filterForm.type) {
    items = items.filter((t) => t.type === filterForm.type);
  }
  return items;
});

const totalRecharge = computed(
  () => filteredTransactions.value.filter((t) => t.type === "recharge").reduce((sum, t) => sum + t.amount, 0).toFixed(2)
);
const totalConsume = computed(
  () => filteredTransactions.value.filter((t) => t.type === "consume").reduce((sum, t) => sum + t.amount, 0).toFixed(2)
);
const totalOpen = computed(
  () => filteredTransactions.value.filter((t) => t.type === "open").length
);

function formatType(type) {
  if (type === "recharge") return "充值";
  if (type === "consume") return "消费";
  if (type === "open") return "开户";
  return type;
}

function getTypeClass(type) {
  if (type === "recharge") return "tx-recharge";
  if (type === "consume") return "tx-consume";
  if (type === "open") return "tx-open";
  return "";
}

function formatAmount(tx) {
  if (tx.type === "recharge") return `+¥${tx.amount}`;
  if (tx.type === "consume") return `-¥${tx.amount}`;
  if (tx.type === "open") return "¥0";
  return `¥${tx.amount}`;
}

onMounted(loadData);
</script>

<template>
  <div class="page-stack">
    <header class="page-header">
      <div>
        <h2>储值流水</h2>
        <p>查询所有充值和消费记录。</p>
      </div>
    </header>

    <div class="stat-grid">
      <div class="stat-card">
        <span>交易笔数</span>
        <strong>{{ filteredTransactions.length }}</strong>
      </div>
      <div class="stat-card">
        <span>开户笔数</span>
        <strong class="tx-open">{{ totalOpen }}</strong>
      </div>
      <div class="stat-card">
        <span>充值总额</span>
        <strong class="tx-recharge">¥{{ totalRecharge }}</strong>
      </div>
      <div class="stat-card">
        <span>消费总额</span>
        <strong class="tx-consume">¥{{ totalConsume }}</strong>
      </div>
    </div>

    <div class="form-panel filter-panel">
      <label>按车牌筛选
        <select v-model="filterForm.plate_number" @change="loadData">
          <option value="">全部车牌</option>
          <option v-for="card in cards" :key="card.id" :value="card.plate_number">
            {{ card.plate_number }} - {{ card.holder_name }}
          </option>
        </select>
      </label>
      <label>按类型筛选
        <select v-model="filterForm.type">
          <option value="">全部类型</option>
          <option value="open">开户</option>
          <option value="recharge">充值</option>
          <option value="consume">消费</option>
        </select>
      </label>
    </div>

    <section class="table-section">
      <h3>流水明细</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>流水号</th>
              <th>车牌</th>
              <th>类型</th>
              <th>金额</th>
              <th>余额</th>
              <th>关联订单</th>
              <th>备注</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tx in filteredTransactions" :key="tx.id">
              <td>#{{ tx.id }}</td>
              <td>{{ tx.plate_number }}</td>
              <td>
                <span class="tx-badge" :class="getTypeClass(tx.type)">{{ formatType(tx.type) }}</span>
              </td>
              <td :class="getTypeClass(tx.type)">
                {{ formatAmount(tx) }}
              </td>
              <td>¥{{ tx.balance_after }}</td>
              <td>{{ tx.related_order_id ? `#${tx.related_order_id}` : "-" }}</td>
              <td>{{ tx.remark || "-" }}</td>
              <td>{{ tx.created_at }}</td>
            </tr>
            <tr v-if="filteredTransactions.length === 0">
              <td colspan="8" style="text-align: center; padding: 32px; color: #65746e;">暂无流水记录</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
