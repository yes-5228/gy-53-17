<script setup>
import { onMounted, reactive, ref } from "vue";
import { parkingApi } from "../api/parking";
import StatusBadge from "../components/StatusBadge.vue";

const cards = ref([]);
const message = ref("");
const rechargeMessage = ref("");
const form = reactive({
  holder_name: "",
  phone: "",
  plate_number: "",
  start_date: new Date().toISOString().slice(0, 10),
  end_date: "",
  fee: 360,
  initial_balance: 0,
});
const rechargeForm = reactive({
  plate_number: "",
  amount: 100,
});
const quickAmounts = [50, 100, 200, 500];

async function loadCards() {
  const data = await parkingApi.getCards();
  cards.value = data.items;
}

async function createCard() {
  message.value = "";
  try {
    await parkingApi.createCard(form);
    Object.assign(form, {
      holder_name: "",
      phone: "",
      plate_number: "",
      start_date: new Date().toISOString().slice(0, 10),
      end_date: "",
      fee: 360,
      initial_balance: 0,
    });
    await loadCards();
    message.value = "月卡办理成功";
  } catch (err) {
    message.value = err.message;
  }
}

async function setStatus(card, status) {
  await parkingApi.updateCard(card.id, { status });
  await loadCards();
}

function openRecharge(card) {
  rechargeForm.plate_number = card.plate_number;
  rechargeForm.amount = 100;
  rechargeMessage.value = "";
}

async function doRecharge() {
  rechargeMessage.value = "";
  try {
    await parkingApi.recharge(rechargeForm);
    rechargeForm.plate_number = "";
    rechargeForm.amount = 100;
    await loadCards();
    rechargeMessage.value = "充值成功";
  } catch (err) {
    rechargeMessage.value = err.message;
  }
}

function setQuickAmount(amount) {
  rechargeForm.amount = amount;
}

onMounted(loadCards);
</script>

<template>
  <div class="page-stack">
    <div class="two-column">
      <section>
        <header class="page-header compact">
          <div>
            <h2>月卡办理</h2>
            <p>登记车主、车牌、有效期与费用，可同时开通储值账户。</p>
          </div>
        </header>
        <form class="form-panel" @submit.prevent="createCard">
          <label>车主姓名<input v-model="form.holder_name" required /></label>
          <label>手机号<input v-model="form.phone" required /></label>
          <label>车牌号<input v-model="form.plate_number" required /></label>
          <label>开始日期<input v-model="form.start_date" type="date" required /></label>
          <label>结束日期<input v-model="form.end_date" type="date" required /></label>
          <label>月卡费用<input v-model.number="form.fee" type="number" min="0" required /></label>
          <label>初始储值金额
            <input v-model.number="form.initial_balance" type="number" min="0" />
            <span class="hint-text">办卡时一并充值，可选</span>
          </label>
          <button class="primary-button" type="submit">办理月卡</button>
          <p v-if="message" class="hint-text">{{ message }}</p>
        </form>
      </section>

      <section>
        <header class="page-header compact">
          <div>
            <h2>储值充值</h2>
            <p>为已有月卡车主进行储值账户充值。</p>
          </div>
        </header>
        <div class="form-panel">
          <label>选择车主
            <select v-model="rechargeForm.plate_number">
              <option value="">请选择车牌</option>
              <option v-for="card in cards" :key="card.id" :value="card.plate_number">
                {{ card.plate_number }} - {{ card.holder_name }} (余额 ¥{{ card.balance || 0 }})
              </option>
            </select>
          </label>
          <label>充值金额
            <input v-model.number="rechargeForm.amount" type="number" min="1" step="0.01" />
          </label>
          <div class="quick-amounts">
            <button
              v-for="amt in quickAmounts"
              :key="amt"
              type="button"
              class="small-button"
              :class="{ active: rechargeForm.amount === amt }"
              @click="setQuickAmount(amt)"
            >
              ¥{{ amt }}
            </button>
          </div>
          <button
            class="primary-button"
            type="button"
            :disabled="!rechargeForm.plate_number || !rechargeForm.amount || rechargeForm.amount <= 0"
            @click="doRecharge"
          >
            确认充值
          </button>
          <p v-if="rechargeMessage" class="hint-text">{{ rechargeMessage }}</p>
        </div>
      </section>
    </div>

    <section class="table-section">
      <h3>月卡列表</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>车主</th>
              <th>车牌</th>
              <th>有效期</th>
              <th>月卡费用</th>
              <th>储值余额</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="card in cards" :key="card.id">
              <td>{{ card.holder_name }}</td>
              <td>{{ card.plate_number }}</td>
              <td>{{ card.start_date }} 至 {{ card.end_date }}</td>
              <td>¥{{ card.fee }}</td>
              <td>
                <strong :class="{ 'balance-positive': (card.balance || 0) > 0 }">
                  ¥{{ card.balance || 0 }}
                </strong>
              </td>
              <td><StatusBadge :status="card.status" /></td>
              <td>
                <div class="action-group">
                  <button class="small-button" type="button" @click="openRecharge(card)">充值</button>
                  <select :value="card.status" @change="setStatus(card, $event.target.value)">
                    <option value="active">有效</option>
                    <option value="paused">暂停</option>
                    <option value="expired">到期</option>
                  </select>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
